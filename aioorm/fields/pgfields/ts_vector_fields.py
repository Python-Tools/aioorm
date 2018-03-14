from aioorm.const import TS_MATCH
from aioorm.ast.function import fn
from aioorm.ast.entity import Expression
from ..text_fields import TextField
from ..field import Field
from .indexed_field_mixin import IndexedFieldMixin


class TSVectorField(IndexedFieldMixin, TextField):
    field_type = 'TSVECTOR'
    default_index_type = 'GIN'
    __hash__ = Field.__hash__

    def match(self, query, language=None):
        params = (language, query) if language is not None else (query,)
        return Expression(self, TS_MATCH, fn.to_tsquery(*params))
