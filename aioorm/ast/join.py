from aioorm.const import JOIN
from .table import BaseTable


class Join(BaseTable):
    def __init__(self, lhs, rhs, join_type=JOIN.INNER, on=None, alias=None):
        super(Join, self).__init__(alias=alias)
        self.lhs = lhs
        self.rhs = rhs
        self.join_type = join_type
        self._on = on

    def on(self, predicate):
        self._on = predicate
        return self

    def __sql__(self, ctx):
        (ctx
         .sql(self.lhs)
         .literal(' %s JOIN ' % self.join_type)
         .sql(self.rhs))
        if self._on is not None:
            ctx.literal(' ON ').sql(self._on)
        return ctx


__all__ = ["Join"]
