import operator
from functools import reduce
from aioorm.const import ROW
from aioorm.utils import database_required
from aioorm.sql_generation.context import Context
from aioorm.ast.node import Node
from aioorm.ast.entity import CommaNodeList


class BaseQuery(Node):
    default_row_type = ROW.DICT

    def __init__(self, _database=None, **kwargs):
        self._database = _database
        self._cursor_wrapper = None
        self._row_type = None
        self._constructor = None
        super().__init__(**kwargs)

    def bind(self, database=None):
        self._database = database
        return self

    def clone(self):
        query = super(BaseQuery, self).clone()
        query._cursor_wrapper = None
        return query

    @Node.copy
    def dicts(self, as_dict=True):
        self._row_type = ROW.DICT if as_dict else None
        return self

    @Node.copy
    def tuples(self, as_tuple=True):
        self._row_type = ROW.TUPLE if as_tuple else None
        return self

    @Node.copy
    def namedtuples(self, as_namedtuple=True):
        self._row_type = ROW.NAMED_TUPLE if as_namedtuple else None
        return self

    @Node.copy
    def objects(self, constructor=None):
        self._row_type = ROW.CONSTRUCTOR if constructor else None
        self._constructor = constructor
        return self

    def _get_cursor_wrapper(self, cursor):
        row_type = self._row_type or self.default_row_type

        if row_type == ROW.DICT:
            return DictCursorWrapper(cursor)
        elif row_type == ROW.TUPLE:
            return CursorWrapper(cursor)
        elif row_type == ROW.NAMED_TUPLE:
            return NamedTupleCursorWrapper(cursor)
        elif row_type == ROW.CONSTRUCTOR:
            return ObjectCursorWrapper(cursor, self._constructor)
        else:
            raise ValueError('Unrecognized row type: "%s".' % row_type)

    def __sql__(self, ctx):
        raise NotImplementedError

    def sql(self):
        if self._database:
            context = self._database.get_sql_context()
        else:
            context = Context()
        return context.parse(self)

    @database_required
    def execute(self, database):
        return self._execute(database)

    def _execute(self, database):
        raise NotImplementedError

    def iterator(self, database=None):
        return iter(self.execute(database).iterator())

    def _ensure_execution(self):
        if not self._cursor_wrapper:
            if not self._database:
                raise ValueError('Query has not been executed.')
            self.execute()

    def __iter__(self):
        self._ensure_execution()
        return iter(self._cursor_wrapper)

    def __getitem__(self, value):
        self._ensure_execution()
        if isinstance(value, slice):
            index = value.stop
        else:
            index = value
        if index is not None and index >= 0:
            index += 1
        self._cursor_wrapper.fill_cache(index)
        return self._cursor_wrapper.row_cache[value]

    def __len__(self):
        self._ensure_execution()
        return len(self._cursor_wrapper)


class RawQuery(BaseQuery):
    def __init__(self, sql=None, params=None, **kwargs):
        super().__init__(**kwargs)
        self._sql = sql
        self._params = params

    def __sql__(self, ctx):
        ctx.literal(self._sql)
        if self._params:
            for param in self._params:
                if isinstance(param, Node):
                    ctx.sql(param)
                else:
                    ctx.value(param)
        return ctx

    def _execute(self, database):
        if self._cursor_wrapper is None:
            cursor = database.execute(self)
            self._cursor_wrapper = self._get_cursor_wrapper(cursor)
        return self._cursor_wrapper


class Query(BaseQuery):
    def __init__(self, where=None, order_by=None, limit=None, offset=None,
                 **kwargs):
        super().__init__(**kwargs)
        self._where = where
        self._order_by = order_by
        self._limit = limit
        self._offset = offset

        self._cte_list = None

    @Node.copy
    def with_cte(self, *cte_list):
        self._cte_list = cte_list

    @Node.copy
    def where(self, *expressions):
        if self._where is not None:
            expressions = (self._where,) + expressions
        self._where = reduce(operator.and_, expressions)

    @Node.copy
    def order_by(self, *values):
        self._order_by = values

    @Node.copy
    def order_by_extend(self, *values):
        self._order_by = ((self._order_by or ()) + values) or None

    @Node.copy
    def limit(self, value=None):
        self._limit = value

    @Node.copy
    def offset(self, value=None):
        self._offset = value

    @Node.copy
    def paginate(self, page, paginate_by=20):
        if page > 0:
            page -= 1
        self._limit = paginate_by
        self._offset = page * paginate_by

    def _apply_ordering(self, ctx):
        if self._order_by:
            (ctx
             .literal(' ORDER BY ')
             .sql(CommaNodeList(self._order_by)))
        if self._limit is not None or (self._offset is not None and
                                       ctx.state.limit_max):
            ctx.literal(' LIMIT %d' % (self._limit or ctx.state.limit_max))
        if self._offset is not None:
            ctx.literal(' OFFSET %d' % self._offset)
        return ctx

    def __sql__(self, ctx):
        if self._cte_list:
            # The CTE scope is only used at the very beginning of the query,
            # when we are describing the various CTEs we will be using.
            recursive = any(cte._recursive for cte in self._cte_list)
            with ctx.scope_cte():
                (ctx
                 .literal('WITH RECURSIVE ' if recursive else 'WITH ')
                 .sql(CommaNodeList(self._cte_list))
                 .literal(' '))
        return ctx
