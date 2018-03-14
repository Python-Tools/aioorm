from aioorm.const import TS_MATCH
from aioorm.ast.entity import Expression
from aioorm.ast.function import fn


def Match(field, query, language=None):
    params = (language, query) if language is not None else (query,)
    field_params = (language, field) if language is not None else (field,)
    return Expression(
        fn.to_tsvector(*field_params),
        TS_MATCH,
        fn.to_tsquery(*params))
