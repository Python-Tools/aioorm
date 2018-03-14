from .entity import ColumnBase, EnclosedNodeList
from .node import Node


class Value(ColumnBase):
    def __init__(self, value, converter=None, unpack=True):
        self.value = value
        self.converter = converter
        self.multi = isinstance(self.value, (list, set, tuple)) and unpack
        if self.multi:
            self.values = []
            for item in self.value:
                if isinstance(item, Node):
                    self.values.append(item)
                else:
                    self.values.append(Value(item, self.converter))

    def __sql__(self, ctx):
        if self.multi:
            ctx.sql(EnclosedNodeList(self.values))
        else:
            (ctx
             .literal(ctx.state.param or '?')
             .value(self.value, self.converter))
        return ctx


def AsIs(value):
    return Value(value, unpack=False)


__all__ = ["Value", "AsIs"]
