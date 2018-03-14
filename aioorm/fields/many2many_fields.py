from aioorm.reflect import is_model
from aioorm.model.model import Model
from .meta_fields import MetaField
from .accessor import ManyToManyFieldAccessor
from .foreignkey_fields import DeferredThroughModel, ForeignKeyField


class ManyToManyField(MetaField):
    accessor_class = ManyToManyFieldAccessor

    def __init__(self, model, backref=None, through_model=None,
                 _is_backref=False):
        if through_model is not None and not (
                isinstance(through_model, DeferredThroughModel) or
                is_model(through_model)):
            raise TypeError('Unexpected value for through_model. Expected '
                            'Model or DeferredThroughModel.')
        self.rel_model = model
        self.backref = backref
        self.through_model = through_model
        self._is_backref = _is_backref

    def _get_descriptor(self):
        return ManyToManyFieldAccessor(self)

    def bind(self, model, name, set_attribute=True):
        if isinstance(self.through_model, DeferredThroughModel):
            self.through_model.set_field(model, self, name)
            return

        super(ManyToManyField, self).bind(model, name, set_attribute)

        if not self._is_backref:
            many_to_many_field = ManyToManyField(
                self.model,
                through_model=self.through_model,
                _is_backref=True)
            backref = self.backref or model._meta.name + 's'
            self.rel_model._meta.add_field(backref, many_to_many_field)

    def get_models(self):
        return [model for _, model in sorted((
            (self._is_backref, self.model),
            (not self._is_backref, self.rel_model)))]

    def get_through_model(self):
        if not self.through_model:
            lhs, rhs = self.get_models()
            tables = [model._meta.table_name for model in (lhs, rhs)]

            class Meta:
                database = self.model._meta.database
                table_name = '%s_%s_through' % tuple(tables)
                indexes = (
                    ((lhs._meta.name, rhs._meta.name),
                     True),)

            attrs = {
                lhs._meta.name: ForeignKeyField(lhs),
                rhs._meta.name: ForeignKeyField(rhs)}
            attrs['Meta'] = Meta

            self.through_model = type(
                '%s%sThrough' % (lhs.__name__, rhs.__name__),
                (Model,),
                attrs)

        return self.through_model
