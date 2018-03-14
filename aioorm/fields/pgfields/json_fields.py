from psycopg2.extras import register_hstore
try:
    from psycopg2.extras import Json
except:
    Json = None
from aioorm.const import (
    JSONB_CONTAINS,
    JSONB_EXISTS,
    JSONB_CONTAINS_ANY_KEY,
    JSONB_CONTAINS_ALL_KEYS,
    JSONB_CONTAINED_BY
)
from aioorm.ast.entity import (
    _LookupNode,
    Expression,
    NodeList,
    SQL
)
from aioorm.ast.node import Node
from aioorm.ast.value import Value
from ..field import Field
from .indexed_field_mixin import IndexedFieldMixin


class _JsonLookupBase(_LookupNode):
    def __init__(self, node, parts, as_json=False):
        super(_JsonLookupBase, self).__init__(node, parts)
        self._as_json = as_json

    def clone(self):
        return type(self)(self.node, list(self.parts), self._as_json)

    @Node.copy
    def as_json(self, as_json=True):
        self._as_json = as_json

    def contains(self, other):
        clone = self.as_json(True)
        if isinstance(other, (list, dict)):
            return Expression(clone, JSONB_CONTAINS, Json(other))
        return Expression(clone, JSONB_EXISTS, other)

    def contains_any(self, *keys):
        return Expression(
            self.as_json(True),
            JSONB_CONTAINS_ANY_KEY,
            Value(list(keys), unpack=False))

    def contains_all(self, *keys):
        return Expression(
            self.as_json(True),
            JSONB_CONTAINS_ALL_KEYS,
            Value(list(keys), unpack=False))


class JsonLookup(_JsonLookupBase):
    def __getitem__(self, value):
        return JsonLookup(self.node, self.parts + [value], self._as_json)

    def __sql__(self, ctx):
        ctx.sql(self.node)
        for part in self.parts[:-1]:
            ctx.literal('->').sql(part)
        if self.parts:
            (ctx
             .literal('->' if self._as_json else '->>')
             .sql(self.parts[-1]))

        return ctx


class JsonPath(_JsonLookupBase):
    def __sql__(self, ctx):
        return (ctx
                .sql(self.node)
                .literal('#>' if self._as_json else '#>>')
                .sql(Value('{%s}' % ','.join(map(str, self.parts)))))


class JSONField(Field):
    field_type = 'JSON'

    def __init__(self, dumps=None, *args, **kwargs):
        if Json is None:
            raise Exception('Your version of psycopg2 does not support JSON.')
        self.dumps = dumps
        super(JSONField, self).__init__(*args, **kwargs)

    def db_value(self, value):
        if value is None:
            return value
        if not isinstance(value, Json):
            return Json(value, dumps=self.dumps)
        return value

    def __getitem__(self, value):
        return JsonLookup(self, [value])

    def path(self, *keys):
        return JsonPath(self, keys)


def cast_jsonb(node):
    return NodeList((node, SQL('::jsonb')), glue='')


class BinaryJSONField(IndexedFieldMixin, JSONField):
    field_type = 'JSONB'
    default_index_type = 'GIN'
    __hash__ = Field.__hash__

    def contains(self, other):
        if isinstance(other, (list, dict)):
            return Expression(self, JSONB_CONTAINS, Json(other))
        return Expression(cast_jsonb(self), JSONB_EXISTS, other)

    def contained_by(self, other):
        return Expression(cast_jsonb(self), JSONB_CONTAINED_BY, Json(other))

    def contains_any(self, *items):
        return Expression(
            cast_jsonb(self),
            JSONB_CONTAINS_ANY_KEY,
            Value(list(items), unpack=False))

    def contains_all(self, *items):
        return Expression(
            cast_jsonb(self),
            JSONB_CONTAINS_ALL_KEYS,
            Value(list(items), unpack=False))
