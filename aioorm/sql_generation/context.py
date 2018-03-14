from contextlib import contextmanager
from aioorm.utils import __scope_context__
from aioorm.const import (
    SCOPE_NORMAL,
    SCOPE_SOURCE,
    SCOPE_VALUES,
    SCOPE_CTE, SCOPE_COLUMN
)
from aioorm.reflect import is_model
from aioorm.ast.node import Node
from .alias_manager import AliasManager
from .state import State


class Context(object):
    def __init__(self, **settings):
        self.stack = []
        self._sql = []
        self._values = []
        self.alias_manager = AliasManager()
        self.state = State(**settings)

    def column_sort_key(self, item):
        return item[0].get_sort_key(self)

    @property
    def scope(self):
        return self.state.scope

    @property
    def parentheses(self):
        return self.state.parentheses

    @property
    def subquery(self):
        return self.state.subquery

    def __call__(self, **overrides):
        if overrides and overrides.get('scope') == self.scope:
            del overrides['scope']

        self.stack.append(self.state)
        self.state = self.state(**overrides)
        return self

    scope_normal = __scope_context__(SCOPE_NORMAL)
    scope_source = __scope_context__(SCOPE_SOURCE)
    scope_values = __scope_context__(SCOPE_VALUES)
    scope_cte = __scope_context__(SCOPE_CTE)
    scope_column = __scope_context__(SCOPE_COLUMN)

    def __enter__(self):
        if self.parentheses:
            self.literal('(')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.parentheses:
            self.literal(')')
        self.state = self.stack.pop()

    @contextmanager
    def push_alias(self):
        self.alias_manager.push()
        yield
        self.alias_manager.pop()

    def sql(self, obj):
        if isinstance(obj, (Node, Context)):
            return obj.__sql__(self)
        elif is_model(obj):
            return obj._meta.table.__sql__(self)
        else:
            return self.sql(Value(obj))

    def literal(self, keyword):
        self._sql.append(keyword)
        return self

    def value(self, value, converter=None):
        if converter is None:
            converter = self.state.converter
        if converter is not None:
            value = converter(value)
        self._values.append(value)
        return self

    def __sql__(self, ctx):
        ctx._sql.extend(self._sql)
        ctx._values.extend(self._values)
        return ctx

    def parse(self, node):
        return self.sql(node).query()

    def query(self):
        return ''.join(self._sql), self._values
