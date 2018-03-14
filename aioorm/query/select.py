import operator
from functools import reduce
from aioorm.const import SCOPE_COLUMN, SCOPE_SOURCE
from aioorm.utils import database_required
from aioorm.ast.node import Node
from aioorm.ast.cte import CTE
from aioorm.ast.source import Source, _HashableSource
from aioorm.ast.entity import SQL, CommaNodeList, EnclosedNodeList
from aioorm.ast.function import fn
from aioorm.ast.table import Table
from aioorm.ast.join import Join
from .base import Query


def __compound_select__(operation, inverted=False):
    def method(self, other):
        if inverted:
            self, other = other, self
        return CompoundSelectQuery(self, operation, other)
    return method


class SelectQuery(Query):
    __add__ = __compound_select__('UNION ALL')
    __or__ = __compound_select__('UNION')
    __and__ = __compound_select__('INTERSECT')
    __sub__ = __compound_select__('EXCEPT')
    __radd__ = __compound_select__('UNION ALL', inverted=True)
    __ror__ = __compound_select__('UNION', inverted=True)
    __rand__ = __compound_select__('INTERSECT', inverted=True)
    __rsub__ = __compound_select__('EXCEPT', inverted=True)

    def cte(self, name, recursive=False, columns=None):
        return CTE(name, self, recursive=recursive, columns=columns)


class SelectBase(_HashableSource, Source, SelectQuery):
    def _get_hash(self):
        return hash((self.__class__, self._alias or id(self)))

    def _execute(self, database):
        if self._cursor_wrapper is None:
            cursor = database.execute(self)
            self._cursor_wrapper = self._get_cursor_wrapper(cursor)
        return self._cursor_wrapper

    @database_required
    def peek(self, database, n=1):
        rows = self.execute(database)[:n]
        if rows:
            return rows[0] if n == 1 else rows

    @database_required
    def first(self, database, n=1):
        if self._limit != n:
            self._limit = n
            self._cursor_wrapper = None
        return self.peek(database, n=n)

    @database_required
    def scalar(self, database, as_tuple=False):
        row = self.tuples().peek(database)
        return row[0] if row and not as_tuple else row

    @database_required
    def count(self, database, clear_limit=False):
        clone = self.order_by().alias('_wrapped')
        if clear_limit:
            clone._limit = clone._offset = None
        try:
            if clone._having is None and clone._windows is None and \
               clone._distinct is None and clone._simple_distinct is not True:
                clone = clone.select(SQL('1'))
        except AttributeError:
            pass
        return Select([clone], [fn.COUNT(SQL('1'))]).scalar(database)

    @database_required
    def exists(self, database):
        clone = self.columns(SQL('1'))
        clone._limit = 1
        clone._offset = None
        return bool(clone.scalar())

    @database_required
    def get(self, database):
        self._cursor_wrapper = None
        try:
            return self.execute(database)[0]
        except IndexError:
            pass


# QUERY IMPLEMENTATIONS.


class CompoundSelectQuery(SelectBase):
    def __init__(self, lhs, op, rhs):
        super().__init__()
        self.lhs = lhs
        self.op = op
        self.rhs = rhs

    @property
    def _returning(self):
        return self.lhs._returning

    def _get_query_key(self):
        return (self.lhs.get_query_key(), self.rhs.get_query_key())

    def __sql__(self, ctx):
        if ctx.scope == SCOPE_COLUMN:
            return self.apply_column(ctx)

        parens_around_query = ctx.state.compound_select_parentheses
        outer_parens = ctx.subquery or (ctx.scope == SCOPE_SOURCE)
        with ctx(parentheses=outer_parens):
            with ctx.scope_normal(parentheses=parens_around_query,
                                  subquery=False):
                ctx.sql(self.lhs)
            ctx.literal(' %s ' % self.op)
            with ctx.push_alias():
                with ctx.scope_normal(parentheses=parens_around_query,
                                      subquery=False):
                    ctx.sql(self.rhs)

            # Apply ORDER BY, LIMIT, OFFSET.
            self._apply_ordering(ctx)

        return self.apply_alias(ctx)


class Select(SelectBase):
    def __init__(self, from_list=None, columns=None, group_by=None,
                 having=None, distinct=None, windows=None, for_update=None,
                 **kwargs):
        super().__init__(**kwargs)
        self._from_list = (list(from_list) if isinstance(from_list, tuple)
                           else from_list) or []
        self._returning = columns
        self._group_by = group_by
        self._having = having
        self._windows = None
        self._for_update = 'FOR UPDATE' if for_update is True else for_update

        self._distinct = self._simple_distinct = None
        if distinct:
            if isinstance(distinct, bool):
                self._simple_distinct = distinct
            else:
                self._distinct = distinct

        self._cursor_wrapper = None

    @Node.copy
    def columns(self, *columns, **kwargs):
        self._returning = columns
    select = columns

    @Node.copy
    def select_extend(self, *columns):
        self._returning = tuple(self._returning) + columns

    @Node.copy
    def from_(self, *sources):
        self._from_list = list(sources)

    @Node.copy
    def join(self, dest, join_type='INNER', on=None):
        if not self._from_list:
            raise ValueError('No sources to join on.')
        item = self._from_list.pop()
        self._from_list.append(Join(item, dest, join_type, on))

    @Node.copy
    def group_by(self, *columns):
        grouping = []
        for column in columns:
            if isinstance(column, Table):
                if not column._columns:
                    raise ValueError('Cannot pass a table to group_by() that '
                                     'does not have columns explicitly '
                                     'declared.')
                grouping.extend([getattr(column, col_name)
                                 for col_name in column._columns])
            else:
                grouping.append(column)
        self._group_by = grouping

    @Node.copy
    def group_by_extend(self, *values):
        group_by = tuple(self._group_by or ()) + values
        return self.group_by(*group_by)

    @Node.copy
    def having(self, *expressions):
        if self._having is not None:
            expressions = (self._having,) + expressions
        self._having = reduce(operator.and_, expressions)

    @Node.copy
    def distinct(self, *columns):
        if len(columns) == 1 and (columns[0] is True or columns[0] is False):
            self._simple_distinct = columns[0]
        else:
            self._simple_distinct = False
            self._distinct = columns

    @Node.copy
    def window(self, *windows):
        self._windows = windows if windows else None

    @Node.copy
    def for_update(self, for_update=True):
        self._for_update = 'FOR UPDATE' if for_update is True else for_update

    def _get_query_key(self):
        return self._alias

    def __sql_selection__(self, ctx, is_subquery=False):
        return ctx.sql(CommaNodeList(self._returning))

    def __sql__(self, ctx):
        super(Select, self).__sql__(ctx)
        if ctx.scope == SCOPE_COLUMN:
            return self.apply_column(ctx)

        is_subquery = ctx.subquery
        parentheses = is_subquery or (ctx.scope == SCOPE_SOURCE)

        with ctx.scope_normal(converter=None, parentheses=parentheses,
                              subquery=True):
            ctx.literal('SELECT ')
            if self._simple_distinct or self._distinct is not None:
                ctx.literal('DISTINCT ')
                if self._distinct:
                    (ctx
                     .literal('ON ')
                     .sql(EnclosedNodeList(self._distinct))
                     .literal(' '))

            with ctx.scope_source():
                ctx = self.__sql_selection__(ctx, is_subquery)

            if self._from_list:
                with ctx.scope_source(parentheses=False):
                    ctx.literal(' FROM ').sql(CommaNodeList(self._from_list))

            if self._where is not None:
                ctx.literal(' WHERE ').sql(self._where)

            if self._group_by:
                ctx.literal(' GROUP BY ').sql(CommaNodeList(self._group_by))

            if self._having is not None:
                ctx.literal(' HAVING ').sql(self._having)

            if self._windows is not None:
                ctx.literal(' WINDOW ')
                ctx.sql(CommaNodeList(self._windows))

            # Apply ORDER BY, LIMIT, OFFSET.
            self._apply_ordering(ctx)

            if self._for_update:
                if not ctx.state.for_update:
                    raise ValueError('FOR UPDATE specified but not supported '
                                     'by database.')
                ctx.literal(' ')
                ctx.sql(SQL(self._for_update))

        ctx = self.apply_alias(ctx)
        return ctx
