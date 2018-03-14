from aioorm.ast.node import Node
from aioorm.ast.entity import CommaNodeList
from .base import Query


class _WriteQuery(Query):
    def __init__(self, table, returning=None, **kwargs):
        self.table = table
        self._returning = returning
        self._return_cursor = True if returning else False
        super().__init__(**kwargs)

    @Node.copy
    def returning(self, *returning):
        self._returning = returning
        self._return_cursor = True if returning else False

    def apply_returning(self, ctx):
        if self._returning:
            ctx.literal(' RETURNING ').sql(CommaNodeList(self._returning))
        return ctx

    def _execute(self, database):
        if self._returning:
            cursor = self.execute_returning(database)
        else:
            cursor = database.execute(self)
        return self.handle_result(database, cursor)

    def execute_returning(self, database):
        if self._cursor_wrapper is None:
            cursor = database.execute(self)
            self._cursor_wrapper = self._get_cursor_wrapper(cursor)
        return self._cursor_wrapper

    def handle_result(self, database, cursor):
        if self._return_cursor:
            return cursor
        return database.rows_affected(cursor)

    def _set_table_alias(self, ctx):
        ctx.alias_manager[self.table] = self.table.__name__

    def __sql__(self, ctx):
        super(_WriteQuery, self).__sql__(ctx)
        # We explicitly set the table alias to the table's name, which ensures
        # that if a sub-select references a column on the outer table, we won't
        # assign it a new alias (e.g. t2) but will refer to it as table.column.
        self._set_table_alias(ctx)
        return ctx
