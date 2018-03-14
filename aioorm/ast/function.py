from .entity import ColumnBase, SQL, NodeList, CommaNodeList, EnclosedNodeList
from .value import Value
from .node import Node
from .window import Window


class Function(ColumnBase):
    def __init__(self, name, arguments, coerce=True):
        self.name = name
        self.arguments = arguments
        if name and name.lower() in ('sum', 'count'):
            self._coerce = False
        else:
            self._coerce = coerce

    def __getattr__(self, attr):
        def decorator(*args, **kwargs):
            return Function(attr, args, **kwargs)
        return decorator

    def over(self, partition_by=None, order_by=None, start=None, end=None,
             window=None):
        if isinstance(partition_by, Window) and window is None:
            window = partition_by
        if start is not None and not isinstance(start, SQL):
            start = SQL(*start)
        if end is not None and not isinstance(end, SQL):
            end = SQL(*end)

        if window is None:
            node = Window(partition_by=partition_by, order_by=order_by,
                          start=start, end=end)
        else:
            node = SQL(window._alias)
        return NodeList((self, SQL('OVER'), node))

    def coerce(self, coerce=True):
        self._coerce = coerce
        return self

    def __sql__(self, ctx):
        ctx.literal(self.name)
        if not len(self.arguments):
            ctx.literal('()')
        else:
            # Special-case to avoid double-wrapping functions whose only
            # argument is a sub-query.
            if len(self.arguments) == 1 and isinstance(self.arguments[0],
                                                       SelectQuery):
                wrapper = CommaNodeList
            else:
                wrapper = EnclosedNodeList
            ctx.sql(wrapper([
                (argument if isinstance(argument, Node)
                 else Value(argument))
                for argument in self.arguments]))
        return ctx


fn = Function(None, None)

__all__ = ["Function", "fn"]
