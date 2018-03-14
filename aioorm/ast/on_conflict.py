import operator
from functools import reduce
from aioorm.reflect import ensure_tuple
from .node import Node


class OnConflict(Node):
    def __init__(self, action=None, update=None, preserve=None, where=None,
                 conflict_target=None):
        self._action = action
        self._update = update
        self._preserve = ensure_tuple(preserve)
        self._where = where
        self._conflict_target = ensure_tuple(conflict_target)

    def get_conflict_statement(self, ctx):
        return ctx.state.conflict_statement(self)

    def get_conflict_update(self, ctx):
        return ctx.state.conflict_update(self)

    @Node.copy
    def preserve(self, *columns):
        self._preserve = columns

    @Node.copy
    def update(self, _data=None, **kwargs):
        if _data and kwargs and not isinstance(_data, dict):
            raise ValueError('Cannot mix data with keyword arguments in the '
                             'OnConflict update method.')
        _data = _data or {}
        if kwargs:
            _data.update(kwargs)
        self._update = _data

    @Node.copy
    def where(self, *expressions):
        if self._where is not None:
            expressions = (self._where,) + expressions
        self._where = reduce(operator.and_, expressions)

    @Node.copy
    def conflict_target(self, *constraints):
        self._conflict_target = constraints
