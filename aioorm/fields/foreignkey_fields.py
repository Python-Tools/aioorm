
from aioorm.utils import __deprecated__
from aioorm.ast.entity import SQL, NodeList, EnclosedNodeList
from .accessor import ForeignKeyAccessor, ObjectIdAccessor, BackrefAccessor
from .field import Field
from .integer_fields import IntegerField, AutoField


class ForeignKeyField(Field):
    accessor_class = ForeignKeyAccessor

    def __init__(self, model, field=None, backref=None, on_delete=None,
                 on_update=None, _deferred=None, rel_model=None, to_field=None,
                 object_id_name=None, related_name=None, *args, **kwargs):
        super(ForeignKeyField, self).__init__(*args, **kwargs)
        if rel_model is not None:
            __deprecated__('"rel_model" has been deprecated in favor of '
                           '"model" for ForeignKeyField objects.')
            model = rel_model
        if to_field is not None:
            __deprecated__('"to_field" has been deprecated in favor of '
                           '"field" for ForeignKeyField objects.')
            field = to_field
        if related_name is not None:
            __deprecated__('"related_name" has been deprecated in favor of '
                           '"backref" for Field objects.')
            backref = related_name

        self.rel_model = model
        self.rel_field = field
        self.declared_backref = backref
        self.backref = None
        self.on_delete = on_delete
        self.on_update = on_update
        self.deferred = _deferred
        self.object_id_name = object_id_name

    def __repr__(self):
        if hasattr(self, 'model') and getattr(self, 'name', None):
            return '<%s: "%s"."%s">' % (type(self).__name__,
                                        self.model._meta.name,
                                        self.name)
        return '<%s: (unbound)>' % type(self).__name__

    @property
    def field_type(self):
        if not isinstance(self.rel_field, AutoField):
            return self.rel_field.field_type
        return IntegerField.field_type

    def get_modifiers(self):
        if not isinstance(self.rel_field, AutoField):
            return self.rel_field.get_modifiers()
        return super(ForeignKeyField, self).get_modifiers()

    def coerce(self, value):
        return self.rel_field.coerce(value)

    def db_value(self, value):
        if isinstance(value, self.rel_model):
            value = value.get_id()
        return self.rel_field.db_value(value)

    def python_value(self, value):
        if isinstance(value, self.rel_model):
            return value
        return self.rel_field.python_value(value)

    def expression(self):
        return self.column == self.rel_field.column

    def bind(self, model, name, set_attribute=True):
        if not self.column_name:
            self.column_name = name if name.endswith('_id') else name + '_id'
        if not self.object_id_name:
            self.object_id_name = self.column_name
            if self.object_id_name == name:
                self.object_id_name += '_id'
        elif self.object_id_name == name:
            raise ValueError('ForeignKeyField "%s"."%s" specifies an '
                             'object_id_name that conflicts with its field '
                             'name.' % (model._meta.name, name))
        if self.rel_model == 'self':
            self.rel_model = model
        if isinstance(self.rel_field, str):
            self.rel_field = getattr(self.rel_model, self.rel_field)
        elif self.rel_field is None:
            self.rel_field = self.rel_model._meta.primary_key

        # Bind field before assigning backref, so field is bound when
        # calling declared_backref() (if callable).
        super(ForeignKeyField, self).bind(model, name, set_attribute)

        if callable(self.declared_backref):
            self.backref = self.declared_backref(self)
        else:
            self.backref, self.declared_backref = self.declared_backref, None
        if not self.backref:
            self.backref = '%s_set' % model._meta.name

        if set_attribute:
            setattr(model, self.object_id_name, ObjectIdAccessor(self))
            if self.backref not in '!+':
                setattr(self.rel_model, self.backref, BackrefAccessor(self))

    def foreign_key_constraint(self):
        parts = [
            SQL('FOREIGN KEY'),
            EnclosedNodeList((self,)),
            SQL('REFERENCES'),
            self.rel_model,
            EnclosedNodeList((self.rel_field,))]
        if self.on_delete:
            parts.append(SQL('ON DELETE %s' % self.on_delete))
        if self.on_update:
            parts.append(SQL('ON UPDATE %s' % self.on_update))
        return NodeList(parts)

    def __getattr__(self, attr):
        if attr.startswith('__'):
            # Prevent recursion error when deep-copying.
            raise AttributeError('Cannot look-up non-existant "__" methods.')
        if attr in self.rel_model._meta.fields:
            return self.rel_model._meta.fields[attr]
        raise AttributeError('%r has no attribute %s, nor is it a valid field '
                             'on %s.' % (self, attr, self.rel_model))


class DeferredForeignKey(Field):
    _unresolved = set()

    def __init__(self, rel_model_name, **kwargs):
        self.field_kwargs = kwargs
        self.rel_model_name = rel_model_name.lower()
        DeferredForeignKey._unresolved.add(self)
        super(DeferredForeignKey, self).__init__()

    __hash__ = object.__hash__

    def set_model(self, rel_model):
        field = ForeignKeyField(rel_model, _deferred=True, **self.field_kwargs)
        self.model._meta.add_field(self.name, field)

    @staticmethod
    def resolve(model_cls):
        unresolved = list(DeferredForeignKey._unresolved)
        for dr in unresolved:
            if dr.rel_model_name == model_cls.__name__.lower():
                dr.set_model(model_cls)
                DeferredForeignKey._unresolved.discard(dr)


class DeferredThroughModel(object):
    def set_field(self, model, field, name):
        self.model = model
        self.field = field
        self.name = name

    def set_model(self, through_model):
        self.field.through_model = through_model
        self.field.bind(self.model, self.name)
