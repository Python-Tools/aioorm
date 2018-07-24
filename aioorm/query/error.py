class QueryError(Exception):
    pass

class SqlEnd(QueryError):
    pass

class ParamError(QueryError):
    pass