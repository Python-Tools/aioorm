from aioorm.const import SCOPE_VALUES
from .entity import Entity, ColumnBase


class Column(ColumnBase):
    def __init__(self, source, name):
        self.source = source
        self.name = name

    def get_sort_key(self, ctx):
        if ctx.scope == SCOPE_VALUES:
            return (self.name,)
        else:
            return self.source.get_sort_key(ctx) + (self.name,)

    def __hash__(self):
        return hash((self.source, self.name))

    def __sql__(self, ctx):
        if ctx.scope == SCOPE_VALUES:
            return ctx.sql(Entity(self.name))
        else:
            with ctx.scope_column():
                return ctx.sql(self.source).literal('.').sql(Entity(self.name))


class ColumnFactory:
    __slots__ = ('node',)

    def __init__(self, node):
        self.node = node

    def __getattr__(self, attr):
        return Column(self.node, attr)


class _DynamicColumn:
    __slots__ = ()

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return ColumnFactory(instance)  # Implements __getattr__().
        return self


class _ExplicitColumn:
    __slots__ = ()

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            raise AttributeError(
                '%s specifies columns explicitly, and does not support '
                'dynamic column lookups.' % instance)
        return self


__all__ = ["Column", "ColumnFactory"]
