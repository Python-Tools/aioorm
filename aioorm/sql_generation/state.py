import collections
from aioorm.const import SCOPE_NORMAL


class State(
        collections.namedtuple(
            '_State',
            ('scope', 'parentheses', 'subquery', 'settings')
        )):
    def __new__(cls, scope=SCOPE_NORMAL, parentheses=False, subquery=False,
                **kwargs):
        return super(State, cls).__new__(cls, scope, parentheses, subquery,
                                         kwargs)

    def __call__(self, scope=None, parentheses=None, subquery=None, **kwargs):
        # All state is "inherited" except parentheses.
        scope = self.scope if scope is None else scope
        subquery = self.subquery if subquery is None else subquery

        # Try to avoid unnecessary dict copying.
        if kwargs and self.settings:
            settings = self.settings.copy()  # Copy original settings dict.
            settings.update(kwargs)  # Update copy with overrides.
        elif kwargs:
            settings = kwargs
        else:
            settings = self.settings
        return State(scope, parentheses, subquery, **settings)

    def __getattr__(self, attr_name):
        return self.settings.get(attr_name)
