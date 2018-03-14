from aioorm.const import SCOPE_CTE
from .source import Source, _HashableSource
from .entity import Entity, EnclosedNodeList


class CTE(_HashableSource, Source):
    def __init__(self, name, query, recursive=False, columns=None):
        self._alias = name
        self._nested_cte_list = query._cte_list
        query._cte_list = ()
        self._query = query
        self._recursive = recursive
        if columns is not None:
            columns = [Entity(c) if isinstance(c, str) else c
                       for c in columns]
        self._columns = columns
        super(CTE, self).__init__(alias=name)

    def _get_hash(self):
        return hash((self.__class__, self._alias, id(self._query)))

    def __sql__(self, ctx):
        if ctx.scope != SCOPE_CTE:
            return ctx.sql(Entity(self._alias))

        with ctx.push_alias():
            ctx.alias_manager[self] = self._alias
            ctx.sql(Entity(self._alias))

            if self._columns:
                ctx.literal(' ').sql(EnclosedNodeList(self._columns))
            ctx.literal(' AS (')
            with ctx.scope_normal():
                ctx.sql(self._query)
            ctx.literal(')')
        return ctx


__all__ = ["CTE"]
