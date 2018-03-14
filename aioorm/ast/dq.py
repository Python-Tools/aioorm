from .entity import ColumnBase
from .node import Node


class DQ(ColumnBase):
    def __init__(self, **query):
        super().__init__()
        self.query = query
        self._negated = False

    @Node.copy
    def __invert__(self):
        self._negated = not self._negated

    def clone(self):
        node = DQ(**self.query)
        node._negated = self._negated
        return node


__all__ = ["DQ"]
