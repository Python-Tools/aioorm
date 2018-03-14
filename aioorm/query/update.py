from aioorm.ast.value import Value
from aioorm.ast.node import Node
from aioorm.ast.entity import NodeList, SQL, CommaNodeList
from .write import _WriteQuery


class Update(_WriteQuery):
    def __init__(self, table, update=None, **kwargs):
        super().__init__(table, **kwargs)
        self._update = update
        self._from = None

    @Node.copy
    def from_(self, *sources):
        self._from = sources

    def __sql__(self, ctx):
        super(Update, self).__sql__(ctx)

        with ctx.scope_values(subquery=True):
            ctx.literal('UPDATE ')

            expressions = []
            for k, v in sorted(self._update.items(), key=ctx.column_sort_key):
                if not isinstance(v, Node):
                    converter = k.db_value if isinstance(k, Field) else None
                    v = Value(v, converter=converter, unpack=False)
                expressions.append(NodeList((k, SQL('='), v)))

            (ctx
             .sql(self.table)
             .literal(' SET ')
             .sql(CommaNodeList(expressions)))

            if self._from:
                ctx.literal(' FROM ').sql(CommaNodeList(self._from))

            if self._where:
                ctx.literal(' WHERE ').sql(self._where)
            self._apply_ordering(ctx)
            return self.apply_returning(ctx)
