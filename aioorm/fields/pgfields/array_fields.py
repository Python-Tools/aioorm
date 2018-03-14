from aioorm.const import (
    OP,
    ACONTAINS,
    ACONTAINS_ANY
)
from aioorm.ast.entity import (
    SQL,
    NodeList,
    Expression,
    ObjectSlice
)
from aioorm.ast.node import Node
from aioorm.ast.value import Value
from ..field import Field
from ..integer_fields import IntegerField
from .indexed_field_mixin import IndexedFieldMixin


class ArrayField(IndexedFieldMixin, Field):
    default_index_type = 'GIN'
    passthrough = True

    def __init__(self, field_class=IntegerField, dimensions=1, *args,
                 **kwargs):
        self.__field = field_class(*args, **kwargs)
        self.dimensions = dimensions
        self.field_type = self.__field.field_type
        super().__init__(*args, **kwargs)

    def ddl_datatype(self, ctx):
        data_type = self.__field.ddl_datatype(ctx)
        return NodeList((data_type, SQL('[]' * self.dimensions)), glue='')

    def db_value(self, value):
        if value is not None:
            if isinstance(value, (list, Node)):
                return value
            return list(value)

    def __getitem__(self, value):
        return ObjectSlice.create(self, value)

    def _e(op):
        def inner(self, rhs):
            return Expression(self, op, ArrayValue(self, rhs))
        return inner
    __eq__ = _e(OP.EQ)
    __ne__ = _e(OP.NE)
    __gt__ = _e(OP.GT)
    __ge__ = _e(OP.GTE)
    __lt__ = _e(OP.LT)
    __le__ = _e(OP.LTE)
    __hash__ = Field.__hash__

    def contains(self, *items):
        return Expression(self, ACONTAINS, ArrayValue(self, items))

    def contains_any(self, *items):
        return Expression(self, ACONTAINS_ANY, ArrayValue(self, items))


class ArrayValue(Node):
    def __init__(self, field, value):
        self.field = field
        self.value = value

    def __sql__(self, ctx):
        return (ctx
                .sql(Value(self.value, unpack=False))
                .literal('::')
                .sql(self.field.ddl_datatype(ctx)))
