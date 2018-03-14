from aioorm.const import (
    HKEY,
    HUPDATE,
    HCONTAINS_DICT,
    HCONTAINS_KEYS,
    HCONTAINS_KEY,
    HCONTAINS_ANY_KEY
)
from aioorm.ast.entity import Expression
from aioorm.ast.value import Value
from aioorm.ast.function import fn
from ..field import Field
from .indexed_field_mixin import IndexedFieldMixin


class HStoreField(IndexedFieldMixin, Field):
    field_type = 'HSTORE'
    __hash__ = Field.__hash__

    def __getitem__(self, key):
        return Expression(self, HKEY, Value(key))

    def keys(self):
        return fn.akeys(self)

    def values(self):
        return fn.avals(self)

    def items(self):
        return fn.hstore_to_matrix(self)

    def slice(self, *args):
        return fn.slice(self, Value(list(args), unpack=False))

    def exists(self, key):
        return fn.exist(self, key)

    def defined(self, key):
        return fn.defined(self, key)

    def update(self, **data):
        return Expression(self, HUPDATE, data)

    def delete(self, *keys):
        return fn.delete(self, Value(list(keys), unpack=False))

    def contains(self, value):
        if isinstance(value, dict):
            rhs = Value(value, unpack=False)
            return Expression(self, HCONTAINS_DICT, rhs)
        elif isinstance(value, (list, tuple)):
            rhs = Value(value, unpack=False)
            return Expression(self, HCONTAINS_KEYS, rhs)
        return Expression(self, HCONTAINS_KEY, value)

    def contains_any(self, *keys):
        return Expression(self, HCONTAINS_ANY_KEY, Value(list(keys),
                                                         unpack=False))
