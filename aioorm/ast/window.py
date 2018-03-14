from aioorm.const import SCOPE_SOURCE
from .node import Node
from .entity import SQL, NodeList, CommaNodeList


class Window(Node):
    CURRENT_ROW = 'CURRENT ROW'

    def __init__(self, partition_by=None, order_by=None, start=None, end=None,
                 alias=None):
        super(Window, self).__init__()
        self.partition_by = partition_by
        self.order_by = order_by
        self.start = start
        self.end = end
        if self.start is None and self.end is not None:
            raise ValueError('Cannot specify WINDOW end without start.')
        self._alias = alias or 'w'

    def alias(self, alias=None):
        self._alias = alias or 'w'
        return self

    @staticmethod
    def following(value=None):
        if value is None:
            return SQL('UNBOUNDED FOLLOWING')
        return SQL('%d FOLLOWING' % value)

    @staticmethod
    def preceding(value=None):
        if value is None:
            return SQL('UNBOUNDED PRECEDING')
        return SQL('%d PRECEDING' % value)

    def __sql__(self, ctx):
        if ctx.scope != SCOPE_SOURCE:
            ctx.literal(self._alias)
            ctx.literal(' AS ')

        with ctx(parentheses=True):
            parts = []
            if self.partition_by:
                parts.extend((
                    SQL('PARTITION BY'),
                    CommaNodeList(self.partition_by)))
            if self.order_by:
                parts.extend((
                    SQL('ORDER BY'),
                    CommaNodeList(self.order_by)))
            if self.start is not None and self.end is not None:
                parts.extend((
                    SQL('ROWS BETWEEN'),
                    self.start,
                    SQL('AND'),
                    self.end))
            elif self.start is not None:
                parts.extend((SQL('ROWS'), self.start))
            ctx.sql(NodeList(parts))
        return ctx

    def clone_base(self):
        return Window(self.partition_by, self.order_by)


__all__ = ["Window"]
