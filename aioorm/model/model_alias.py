from aioorm.const import SCOPE_VALUES, SCOPE_SOURCE
from aioorm.ast.node import Node
from aioorm.ast.entity import Entity
from aioorm.fields.field import Field, FieldAlias


class ModelAlias(Node):
    """Provide a separate reference to a model in a query."""

    def __init__(self, model, alias=None):
        self.__dict__['model'] = model
        self.__dict__['alias'] = alias

    def __getattr__(self, attr):
        model_attr = getattr(self.model, attr)
        if isinstance(model_attr, Field):
            self.__dict__[attr] = FieldAlias.create(self, model_attr)
            return self.__dict__[attr]
        return model_attr

    def __setattr__(self, attr, value):
        raise AttributeError('Cannot set attributes on model aliases.')

    def get_field_aliases(self):
        return [getattr(self, n) for n in self.model._meta.sorted_field_names]

    def select(self, *selection):
        if not selection:
            selection = self.get_field_aliases()
        return ModelSelect(self, selection)

    def __call__(self, **kwargs):
        return self.model(**kwargs)

    def __sql__(self, ctx):
        if ctx.scope == SCOPE_VALUES:
            # Return the quoted table name.
            return ctx.sql(self.model)

        if self.alias:
            ctx.alias_manager[self] = self.alias

        if ctx.scope == SCOPE_SOURCE:
            # Define the table and its alias.
            return (ctx
                    .sql(self.model._meta.entity)
                    .literal(' AS ')
                    .sql(Entity(ctx.alias_manager[self])))
        else:
            # Refer to the table using the alias.
            return ctx.sql(Entity(ctx.alias_manager[self]))
