#import asyncio
import threading
from aioorm.const import FIELD, OP, SENTINEL
from aioorm.error import OperationalError, __exception_wrapper__
from aioorm.utils import merge_dict, __deprecated__, _callable_context_manager
from aioorm.sql_generation.context import Context
from aioorm.transaction import _manual, _atomic, _transaction, _savepoint
from .connect import _ConnectionLocal, _ConnectionState, _NoopLock, ConnectionContext


class Database(_callable_context_manager):
    context_class = Context
    field_types = {}
    operations = {}
    param = '?'
    quote = '"'

    # Feature toggles.
    commit_select = False
    compound_select_parentheses = False
    for_update = False
    limit_max = None
    returning_clause = False
    safe_create_index = True
    safe_drop_index = True
    sequences = False

    def __init__(self, database, thread_safe=True, autorollback=False,
                 field_types=None, operations=None, autocommit=None, **kwargs):
        self._field_types = merge_dict(FIELD, self.field_types)
        self._operations = merge_dict(OP, self.operations)
        if field_types:
            self._field_types.update(field_types)
        if operations:
            self._operations.update(operations)

        self.autorollback = autorollback
        self.thread_safe = thread_safe
        if thread_safe:
            self._state = _ConnectionLocal()
            self._lock = threading.Lock()
        else:
            self._state = _ConnectionState()
            self._lock = _NoopLock()

        if autocommit is not None:
            __deprecated__('Peewee no longer uses the "autocommit" option, as '
                           'the semantics now require it to always be True. '
                           'Because some database-drivers also use the '
                           '"autocommit" parameter, you are receiving a '
                           'warning so you may update your code and remove '
                           'the parameter, as in the future, specifying '
                           'autocommit could impact the behavior of the '
                           'database driver you are using.')

        self.connect_params = {}
        self.init(database, **kwargs)

    def init(self, database, **kwargs):
        if not self.is_closed():
            self.close()
        self.database = database
        self.connect_params.update(kwargs)
        self.deferred = not bool(database)

    def __enter__(self):
        if self.is_closed():
            self.connect()
        self.transaction().__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        top = self._state.transactions[-1]
        try:
            top.__exit__(exc_type, exc_val, exc_tb)
        finally:
            self.close()

    def connection_context(self):
        return ConnectionContext(self)

    def _connect(self):
        raise NotImplementedError

    def connect(self, reuse_if_open=False):
        with self._lock:
            if self.deferred:
                raise Exception('Error, database must be initialized before '
                                'opening a connection.')
            if not self._state.closed:
                if reuse_if_open:
                    return False
                raise OperationalError('Connection already opened.')

            self._state.reset()
            with __exception_wrapper__:
                self._state.set_connection(self._connect())
                self._initialize_connection(self._state.conn)
        return True

    def _initialize_connection(self, conn):
        pass

    def close(self):
        with self._lock:
            if self.deferred:
                raise Exception('Error, database must be initialized before '
                                'opening a connection.')
            if self.in_transaction():
                raise OperationalError('Attempting to close database while '
                                       'transaction is open.')
            is_open = not self._state.closed
            try:
                if is_open:
                    with __exception_wrapper__:
                        self._close(self._state.conn)
            finally:
                self._state.reset()
            return is_open

    def _close(self, conn):
        conn.close()

    def is_closed(self):
        return self._state.closed

    def connection(self):
        if self.is_closed():
            self.connect()
        return self._state.conn

    def cursor(self, commit=None):
        if self.is_closed():
            self.connect()
        return self._state.conn.cursor()

    def execute_sql(self, sql, params=None, commit=SENTINEL):
        logger.debug((sql, params))
        if commit is SENTINEL:
            if self.in_transaction():
                commit = False
            elif self.commit_select:
                commit = True
            else:
                commit = not sql[:6].lower().startswith('select')

        with __exception_wrapper__:
            cursor = self.cursor(commit)
            try:
                cursor.execute(sql, params or ())
            except Exception:
                if self.autorollback and not self.in_transaction():
                    self.rollback()
                raise
            else:
                if commit and not self.in_transaction():
                    self.commit()
        return cursor

    def execute(self, query, commit=SENTINEL, **context_options):
        ctx = self.get_sql_context(**context_options)
        sql, params = ctx.sql(query).query()
        return self.execute_sql(sql, params, commit=commit)

    def get_context_options(self):
        return {
            'field_types': self._field_types,
            'operations': self._operations,
            'param': self.param,
            'quote': self.quote,
            'compound_select_parentheses': self.compound_select_parentheses,
            'conflict_statement': self.conflict_statement,
            'conflict_update': self.conflict_update,
            'for_update': self.for_update,
            'limit_max': self.limit_max,
        }

    def get_sql_context(self, **context_options):
        context = self.get_context_options()
        if context_options:
            context.update(context_options)
        return self.context_class(**context)

    def conflict_statement(self, on_conflict):
        raise NotImplementedError

    def conflict_update(self, on_conflict):
        raise NotImplementedError

    def last_insert_id(self, cursor, query_type=None):
        return cursor.lastrowid

    def rows_affected(self, cursor):
        return cursor.rowcount

    def default_values_insert(self, ctx):
        return ctx.literal('DEFAULT VALUES')

    def in_transaction(self):
        return bool(self._state.transactions)

    def push_transaction(self, transaction):
        self._state.transactions.append(transaction)

    def pop_transaction(self):
        return self._state.transactions.pop()

    def transaction_depth(self):
        return len(self._state.transactions)

    def top_transaction(self):
        if self._state.transactions:
            return self._state.transactions[-1]

    def atomic(self):
        return _atomic(self)

    def manual_commit(self):
        return _manual(self)

    def transaction(self):
        return _transaction(self)

    def savepoint(self):
        return _savepoint(self)

    def begin(self):
        if self.is_closed():
            self.connect()

    def commit(self):
        return self._state.conn.commit()

    def rollback(self):
        return self._state.conn.rollback()

    def table_exists(self, table, schema=None):
        return table.__name__ in self.get_tables(schema=schema)

    def get_tables(self, schema=None):
        raise NotImplementedError

    def get_indexes(self, table, schema=None):
        raise NotImplementedError

    def get_columns(self, table, schema=None):
        raise NotImplementedError

    def get_primary_keys(self, table, schema=None):
        raise NotImplementedError

    def get_foreign_keys(self, table, schema=None):
        raise NotImplementedError

    def sequence_exists(self, seq):
        raise NotImplementedError

    def create_tables(self, models, **options):
        for model in sort_models(models):
            model.create_table(**options)

    def drop_tables(self, models, **kwargs):
        for model in reversed(sort_models(models)):
            model.drop_table(**kwargs)

    def extract_date(self, date_part, date_field):
        raise NotImplementedError

    def truncate_date(self, date_part, date_field):
        raise NotImplementedError

    def bind(self, models, bind_refs=True, bind_backrefs=True):
        for model in models:
            model.bind(self, bind_refs=bind_refs, bind_backrefs=bind_backrefs)

    def bind_ctx(self, models, bind_refs=True, bind_backrefs=True):
        return _BoundModelsContext(models, self, bind_refs, bind_backrefs)

    def get_noop_select(self, ctx):
        return ctx.sql(Select().columns(SQL('0')).where(SQL('0')))
