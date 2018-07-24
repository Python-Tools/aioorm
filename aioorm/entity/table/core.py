#!/usr/bin/env python
from copy import deepcopy
MODEL_BASE = '_metaclass_helper_'

class TableMeta(type):
    inheritable = set(['constraints', 'database', 'indexes', 'primary_key',
                       'options', 'schema', 'table_function', 'temporary',
                       'only_save_dirty', 'legacy_table_names'])

    def __new__(cls, name, bases, attrs):
        if name == MODEL_BASE or bases[0].__name__ == MODEL_BASE:
            return super(TableMeta, cls).__new__(cls, name, bases, attrs)

        meta_options = {}
        meta = attrs.pop('Meta', None)
        if meta:
            for k, v in meta.__dict__.items():
                if not k.startswith('_'):
                    meta_options[k] = v

        pk = getattr(meta, 'primary_key', None)
        pk_name = parent_pk = None

        # Inherit any field descriptors by deep copying the underlying field
        # into the attrs of the new model, additionally see if the bases define
        # inheritable model options and swipe them.
        for b in bases:
            if not hasattr(b, '_meta'):
                continue

            base_meta = b._meta
            if parent_pk is None:
                parent_pk = deepcopy(base_meta.primary_key)
            all_inheritable = cls.inheritable | base_meta._additional_keys
            for k in base_meta.__dict__:
                if k in all_inheritable and k not in meta_options:
                    meta_options[k] = base_meta.__dict__[k]
            meta_options.setdefault('schema', base_meta.schema)

            for (k, v) in b.__dict__.items():
                if k in attrs: continue

                if isinstance(v, FieldAccessor) and not v.field.primary_key:
                    attrs[k] = deepcopy(v.field)

        sopts = meta_options.pop('schema_options', None) or {}
        Meta = meta_options.get('model_metadata_class', Metadata)
        Schema = meta_options.get('schema_manager_class', SchemaManager)

        # Construct the new class.
        cls = super(ModelBase, cls).__new__(cls, name, bases, attrs)
        cls.__data__ = cls.__rel__ = None

        cls._meta = Meta(cls, **meta_options)
        cls._schema = Schema(cls, **sopts)

        fields = []
        for key, value in cls.__dict__.items():
            if isinstance(value, Field):
                if value.primary_key and pk:
                    raise ValueError('over-determined primary key %s.' % name)
                elif value.primary_key:
                    pk, pk_name = value, key
                else:
                    fields.append((key, value))

        if pk is None:
            if parent_pk is not False:
                pk, pk_name = ((parent_pk, parent_pk.name)
                               if parent_pk is not None else
                               (AutoField(), 'id'))
            else:
                pk = False
        elif isinstance(pk, CompositeKey):
            pk_name = '__composite_key__'
            cls._meta.composite_key = True

        if pk is not False:
            cls._meta.set_primary_key(pk_name, pk)

        for name, field in fields:
            cls._meta.add_field(name, field)

        # Create a repr and error class before finalizing.
        if hasattr(cls, '__str__') and '__repr__' not in attrs:
            setattr(cls, '__repr__', lambda self: '<%s: %s>' % (
                cls.__name__, self.__str__()))

        exc_name = '%sDoesNotExist' % cls.__name__
        exc_attrs = {'__module__': cls.__module__}
        exception_class = type(exc_name, (DoesNotExist,), exc_attrs)
        cls.DoesNotExist = exception_class

        # Call validation hook, allowing additional model validation.
        cls.validate_model()
        DeferredForeignKey.resolve(cls)
        return cls

    def __repr__(self):
        return '<Model: %s>' % self.__name__

    def __iter__(self):
        return iter(self.select())

    def __getitem__(self, key):
        return self.get_by_id(key)

    def __setitem__(self, key, value):
        self.set_by_id(key, value)

    def __delitem__(self, key):
        self.delete_by_id(key)

    def __contains__(self, key):
        try:
            self.get_by_id(key)
        except self.DoesNotExist:
            return False
        else:
            return True

    def __len__(self):
        return self.select().count()
    def __bool__(self): return True
    __nonzero__ = __bool__  # Python 2.







class TableBase(metaclass=TableMeta):
    "表格的描述"
    pass
    

class Table(TableBase):
    pass