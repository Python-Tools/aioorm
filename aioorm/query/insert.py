import itertools
import collections
from aioorm.ast.entity import SQL, CommaNodeList, EnclosedNodeList
from aioorm.ast.value import Value
from aioorm.ast.on_conflict import OnConflict
from aioorm.ast.node import Node
from .write import _WriteQuery
from .select import SelectQuery


class Insert(_WriteQuery):
    SIMPLE = 0
    QUERY = 1
    MULTI = 2

    class DefaultValuesException(Exception):
        pass

    def __init__(self, table, insert=None, columns=None, on_conflict=None,
                 **kwargs):
        super().__init__(table, **kwargs)
        self._insert = insert
        self._columns = columns
        self._on_conflict = on_conflict
        self._query_type = None

    def where(self, *expressions):
        raise NotImplementedError('INSERT queries cannot have a WHERE clause.')

    @Node.copy
    def on_conflict_ignore(self, ignore=True):
        self._on_conflict = OnConflict('IGNORE') if ignore else None

    @Node.copy
    def on_conflict_replace(self, replace=True):
        self._on_conflict = OnConflict('REPLACE') if replace else None

    @Node.copy
    def on_conflict(self, *args, **kwargs):
        self._on_conflict = (OnConflict(*args, **kwargs) if (args or kwargs)
                             else None)

    def _simple_insert(self, ctx):
        if not self._insert:
            raise self.DefaultValuesException('Error: no data to insert.')
        return self._generate_insert((self._insert,), ctx)

    def get_default_data(self):
        return {}

    def _generate_insert(self, insert, ctx):
        rows_iter = iter(insert)
        columns = self._columns

        # Load and organize column defaults (if provided).
        defaults = self.get_default_data()

        if not columns:
            uses_strings = False
            try:
                row = next(rows_iter)
            except StopIteration:
                raise self.DefaultValuesException('Error: no rows to insert.')
            else:
                accum = []
                value_lookups = {}
                for key in row:
                    if isinstance(key, str):
                        column = getattr(self.table, key)
                        uses_strings = True
                    else:
                        column = key
                    accum.append(column)
                    value_lookups[column] = key

            column_set = set(accum)
            for column in (set(defaults) - column_set):
                accum.append(column)
                value_lookups[column] = column.name if uses_strings else column

            columns = sorted(accum, key=lambda obj: obj.get_sort_key(ctx))
            rows_iter = itertools.chain(iter((row,)), rows_iter)
        else:
            columns = list(columns)
            value_lookups = dict((column, column) for column in columns)
            for col in sorted(defaults, key=lambda obj: obj.get_sort_key(ctx)):
                if col not in value_lookups:
                    columns.append(col)
                    value_lookups[col] = col

        ctx.sql(EnclosedNodeList(columns)).literal(' VALUES ')
        columns_converters = [
            (column, column.db_value if isinstance(column, Field) else None)
            for column in columns]

        all_values = []
        for row in rows_iter:
            values = []
            is_dict = isinstance(row, collections.Mapping)
            for i, (column, converter) in enumerate(columns_converters):
                try:
                    if is_dict:
                        val = row[value_lookups[column]]
                    else:
                        val = row[i]
                except (KeyError, IndexError):
                    if column in defaults:
                        val = defaults[column]
                        if callable(val):
                            val = val()
                    else:
                        raise ValueError('Missing value for "%s".' % column)

                if not isinstance(val, Node):
                    val = Value(val, converter=converter, unpack=False)
                values.append(val)

            all_values.append(EnclosedNodeList(values))

        with ctx.scope_values(subquery=True):
            return ctx.sql(CommaNodeList(all_values))

    def _query_insert(self, ctx):
        return (ctx
                .sql(EnclosedNodeList(self._columns))
                .literal(' ')
                .sql(self._insert))

    def _default_values(self, ctx):
        if not self._database:
            return ctx.literal('DEFAULT VALUES')
        return self._database.default_values_insert(ctx)

    def __sql__(self, ctx):
        super(Insert, self).__sql__(ctx)
        with ctx.scope_values():
            statement = None
            if self._on_conflict is not None:
                statement = self._on_conflict.get_conflict_statement(ctx)

            (ctx
             .sql(statement or SQL('INSERT'))
             .literal(' INTO ')
             .sql(self.table)
             .literal(' '))

            if isinstance(self._insert, dict) and not self._columns:
                try:
                    self._simple_insert(ctx)
                except self.DefaultValuesException:
                    self._default_values(ctx)
                self._query_type = Insert.SIMPLE
            elif isinstance(self._insert, SelectQuery):
                self._query_insert(ctx)
                self._query_type = Insert.QUERY
            else:
                try:
                    self._generate_insert(self._insert, ctx)
                except self.DefaultValuesException:
                    return
                self._query_type = Insert.MULTI

            if self._on_conflict is not None:
                update = self._on_conflict.get_conflict_update(ctx)
                if update is not None:
                    ctx.literal(' ').sql(update)

            return self.apply_returning(ctx)

    def _execute(self, database):
        if self._returning is None and database.returning_clause \
           and self.table._primary_key:
            self._returning = (self.table._primary_key,)
        return super(Insert, self)._execute(database)

    def handle_result(self, database, cursor):
        if self._return_cursor:
            return cursor
        return database.last_insert_id(cursor, self._query_type)
