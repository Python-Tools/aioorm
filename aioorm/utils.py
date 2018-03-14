import warnings
from functools import wraps
from contextlib import contextmanager
from aioorm.const import MODEL_BASE
from aioorm.ast.join import Join


def __deprecated__(s):
    warnings.warn(s, DeprecationWarning)


def __scope_context__(scope):
    @contextmanager
    def inner(self, **kwargs):
        with self(scope=scope, **kwargs):
            yield self
    return inner


class _callable_context_manager:
    def __call__(self, fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            with self:
                return fn(*args, **kwargs)
        return inner


def with_metaclass(meta, base=object):
    return meta(MODEL_BASE, (base,), {})


def merge_dict(source, overrides):
    merged = source.copy()
    if overrides:
        merged.update(overrides)
    return merged


def __bind_database__(meth):
    @wraps(meth)
    def inner(self, *args, **kwargs):
        result = meth(self, *args, **kwargs)
        if self._database:
            return result.bind(self._database)
        return result
    return inner


def __join__(join_type='INNER', inverted=False):
    def method(self, other):
        if inverted:
            self, other = other, self
        return Join(self, other, join_type=join_type)
    return method


def quote(path, quote_char):
    quotes = (quote_char, quote_char)
    if len(path) == 1:
        return path[0].join(quotes)
    return '.'.join([part.join(quotes) for part in path])


def database_required(method):
    @wraps(method)
    def inner(self, database=None, *args, **kwargs):
        database = self._database if database is None else database
        if not database:
            raise Exception('Query must be bound to a database in order '
                            'to call "%s".' % method.__name__)
        return method(self, database, *args, **kwargs)
    return inner


def __pragma__(name):
    def __get__(self):
        return self.pragma(name)

    def __set__(self, value):
        return self.pragma(name, value)
    return property(__get__, __set__)
