from aioorm.utils import __bind_database__, __join__, _callable_context_manager
from aioorm.const import SCOPE_VALUES, SCOPE_SOURCE, JOIN
from .source import _HashableSource, Source
from .column import Column, _ExplicitColumn
from .entity import Entity


class BaseTable(Source):
    __and__ = __join__(JOIN.INNER)
    __add__ = __join__(JOIN.LEFT_OUTER)
    __sub__ = __join__(JOIN.RIGHT_OUTER)
    __or__ = __join__(JOIN.FULL_OUTER)
    __mul__ = __join__(JOIN.CROSS)
    __rand__ = __join__(JOIN.INNER, inverted=True)
    __radd__ = __join__(JOIN.LEFT_OUTER, inverted=True)
    __rsub__ = __join__(JOIN.RIGHT_OUTER, inverted=True)
    __ror__ = __join__(JOIN.FULL_OUTER, inverted=True)
    __rmul__ = __join__(JOIN.CROSS, inverted=True)


class _BoundTableContext(_callable_context_manager):
    def __init__(self, table, database):
        self.table = table
        self.database = database

    def __enter__(self):
        self._orig_database = self.table._database
        self.table.bind(self.database)
        if self.table._model is not None:
            self.table._model.bind(self.database)
        return self.table

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.table.bind(self._orig_database)
        if self.table._model is not None:
            self.table._model.bind(self._orig_database)


class Table(_HashableSource, BaseTable):
    def __init__(self, name, columns=None, primary_key=None, schema=None,
                 alias=None, _model=None, _database=None):
        self.__name__ = name
        self._columns = columns
        self._primary_key = primary_key
        self._schema = schema
        self._path = (schema, name) if schema else (name,)
        self._model = _model
        self._database = _database
        super(Table, self).__init__(alias=alias)

        # Allow tables to restrict what columns are available.
        if columns is not None:
            self.c = _ExplicitColumn()
            for column in columns:
                setattr(self, column, Column(self, column))

        if primary_key:
            col_src = self if self._columns else self.c
            self.primary_key = getattr(col_src, primary_key)
        else:
            self.primary_key = None

    def clone(self):
        # Ensure a deep copy of the column instances.
        return Table(
            self.__name__,
            columns=self._columns,
            primary_key=self._primary_key,
            schema=self._schema,
            alias=self._alias,
            _model=self._model,
            _database=self._database)

    def bind(self, database=None):
        self._database = database
        return self

    def bind_ctx(self, database=None):
        return _BoundTableContext(self, database)

    def _get_hash(self):
        return hash((self.__class__, self._path, self._alias, self._model))

    @__bind_database__
    def select(self, *columns):
        if not columns and self._columns:
            columns = [Column(self, column) for column in self._columns]
        return Select((self,), columns)

    @__bind_database__
    def insert(self, insert=None, columns=None, **kwargs):
        if kwargs:
            insert = {} if insert is None else insert
            src = self if self._columns else self.c
            for key, value in kwargs.items():
                insert[getattr(src, key)] = value
        return Insert(self, insert=insert, columns=columns)

    @__bind_database__
    def replace(self, insert=None, columns=None, **kwargs):
        return (self
                .insert(insert=insert, columns=columns)
                .on_conflict('REPLACE'))

    @__bind_database__
    def update(self, update=None, **kwargs):
        if kwargs:
            update = {} if update is None else update
            for key, value in kwargs.items():
                src = self if self._columns else self.c
                update[getattr(self, key)] = value
        return Update(self, update=update)

    @__bind_database__
    def delete(self):
        return Delete(self)

    def __sql__(self, ctx):
        if ctx.scope == SCOPE_VALUES:
            # Return the quoted table name.
            return ctx.sql(Entity(*self._path))

        if self._alias:
            ctx.alias_manager[self] = self._alias

        if ctx.scope == SCOPE_SOURCE:
            # Define the table and its alias.
            return self.apply_alias(ctx.sql(Entity(*self._path)))
        else:
            # Refer to the table using the alias.
            return self.apply_column(ctx)

__all__=["Table"]