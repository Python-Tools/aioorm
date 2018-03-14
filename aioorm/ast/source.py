from aioorm.const import SCOPE_SOURCE, JOIN
from .node import Node
from .column import _DynamicColumn
from .entity import Entity


class Source(Node):
    c = _DynamicColumn()

    def __init__(self, alias=None):
        super(Source, self).__init__()
        self._alias = alias

    @Node.copy
    def alias(self, name):
        self._alias = name

    def select(self, *columns):
        return Select((self,), columns)

    def join(self, dest, join_type='INNER', on=None):
        return Join(self, dest, join_type, on)

    def left_outer_join(self, dest, on=None):
        return Join(self, dest, JOIN.LEFT_OUTER, on)

    def get_sort_key(self, ctx):
        if self._alias:
            return (self._alias,)
        return (ctx.alias_manager[self],)

    def apply_alias(self, ctx):
        # If we are defining the source, include the "AS alias" declaration. An
        # alias is created for the source if one is not already defined.
        if ctx.scope == SCOPE_SOURCE:
            if self._alias:
                ctx.alias_manager[self] = self._alias
            ctx.literal(' AS ').sql(Entity(ctx.alias_manager[self]))
        return ctx

    def apply_column(self, ctx):
        if self._alias:
            ctx.alias_manager[self] = self._alias
        return ctx.sql(Entity(ctx.alias_manager[self]))


class _HashableSource(object):
    def __init__(self, *args, **kwargs):
        super(_HashableSource, self).__init__(*args, **kwargs)
        self._update_hash()

    @Node.copy
    def alias(self, name):
        self._alias = name
        self._update_hash()

    def _update_hash(self):
        self._hash = self._get_hash()

    def _get_hash(self):
        return hash((self.__class__, self._path, self._alias))

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return self._hash == other._hash

    def __ne__(self, other):
        return not (self == other)


__all__ = ["Source"]
