from aioorm.const import SCOPE_VALUES
from aioorm.utils import merge_dict
from aioorm.reflect import is_model
from aioorm.index import Index
from aioorm.ast.node import Node
from aioorm.ast.entity import SQL, NodeList, EnclosedNodeList, Entity
from aioorm.fields.foreignkey_fields import ForeignKeyField


class SchemaManager(object):
    def __init__(self, model, database=None, **context_options):
        self.model = model
        self._database = database
        context_options.setdefault('scope', SCOPE_VALUES)
        self.context_options = context_options

    @property
    def database(self):
        return self._database or self.model._meta.database

    @database.setter
    def database(self, value):
        self._database = value

    def _create_context(self):
        return self.database.get_sql_context(**self.context_options)

    def _create_table(self, safe=True, **options):
        is_temp = options.pop('temporary', False)
        ctx = self._create_context()
        ctx.literal('CREATE TEMPORARY TABLE ' if is_temp else 'CREATE TABLE ')
        if safe:
            ctx.literal('IF NOT EXISTS ')
        ctx.sql(self.model).literal(' ')

        columns = []
        constraints = []
        meta = self.model._meta
        if meta.composite_key:
            pk_columns = [meta.fields[field_name].column
                          for field_name in meta.primary_key.field_names]
            constraints.append(NodeList((SQL('PRIMARY KEY'),
                                         EnclosedNodeList(pk_columns))))

        for field in meta.sorted_fields:
            columns.append(field.ddl(ctx))
            if isinstance(field, ForeignKeyField) and not field.deferred:
                constraints.append(field.foreign_key_constraint())

        if meta.constraints:
            constraints.extend(meta.constraints)

        constraints.extend(self._create_table_option_sql(options))
        ctx.sql(EnclosedNodeList(columns + constraints))

        if meta.without_rowid:
            ctx.literal(' WITHOUT ROWID')
        return ctx

    def _create_table_option_sql(self, options):
        accum = []
        options = merge_dict(self.model._meta.options or {}, options)
        if not options:
            return accum

        for key, value in sorted(options.items()):
            if not isinstance(value, Node):
                if is_model(value):
                    value = value._meta.table
                else:
                    value = SQL(value)
            accum.append(NodeList((SQL(key), value), glue='='))
        return accum

    def create_table(self, safe=True, **options):
        self.database.execute(self._create_table(safe=safe, **options))

    def _drop_table(self, safe=True, **options):
        is_temp = options.pop('temporary', False)
        ctx = (self._create_context()
               .literal('DROP TEMPORARY ' if is_temp else 'DROP ')
               .literal('TABLE IF EXISTS ' if safe else 'TABLE ')
               .sql(self.model))
        if options.get('cascade'):
            ctx = ctx.literal(' CASCADE')
        return ctx

    def drop_table(self, safe=True, **options):
        self.database.execute(self._drop_table(safe=safe), **options)

    def _create_indexes(self, safe=True):
        return [self._create_index(index, safe)
                for index in self.model._meta.fields_to_index()]

    def _create_index(self, index, safe=True):
        if isinstance(index, Index):
            if not self.database.safe_create_index:
                index = index.safe(False)
            elif index._safe != safe:
                index = index.safe(safe)
        return self._create_context().sql(index)

    def create_indexes(self, safe=True):
        for query in self._create_indexes(safe=safe):
            self.database.execute(query)

    def _drop_indexes(self, safe=True):
        return [self._drop_index(index, safe)
                for index in self.model._meta.fields_to_index()
                if isinstance(index, Index)]

    def _drop_index(self, index, safe):
        statement = 'DROP INDEX '
        if safe and self.database.safe_drop_index:
            statement += 'IF EXISTS '
        return (self
                ._create_context()
                .literal(statement)
                .sql(Entity(index._name)))

    def drop_indexes(self, safe=True):
        for query in self._drop_indexes(safe=safe):
            self.database.execute(query)

    def _check_sequences(self, field):
        if not field.sequence or not self.database.sequences:
            raise ValueError('Sequences are either not supported, or are not '
                             'defined for "%s".' % field.name)

    def _create_sequence(self, field):
        self._check_sequences(field)
        if not self.database.sequence_exists(field.sequence):
            return (self
                    ._create_context()
                    .literal('CREATE SEQUENCE ')
                    .sql(Entity(field.sequence)))

    def create_sequence(self, field):
        self.database.execute(self._create_sequence(field))

    def _drop_sequence(self, field):
        self._check_sequences(field)
        if self.database.sequence_exists(field.sequence):
            return (self
                    ._create_context()
                    .literal('DROP SEQUENCE ')
                    .sql(Entity(field.sequence)))

    def drop_sequence(self, field):
        self.database.execute(self._drop_sequence(field))

    def _create_foreign_key(self, field):
        name = 'fk_%s_%s_refs_%s' % (field.model._meta.table_name,
                                     field.column_name,
                                     field.rel_model._meta.table_name)
        return (self
                ._create_context()
                .literal('ALTER TABLE ')
                .sql(field.model)
                .literal(' ADD CONSTRAINT ')
                .sql(Entity(name))
                .literal(' ')
                .sql(field.foreign_key_constraint()))

    def create_foreign_key(self, field):
        self.database.execute(self._create_foreign_key(field))

    def create_all(self, safe=True, **table_options):
        if self.database.sequences:
            for field in self.model._meta.sorted_fields:
                if field and field.sequence:
                    self.create_sequence(field)

        self.create_table(safe, **table_options)
        self.create_indexes(safe=safe)

    def drop_all(self, safe=True, **options):
        self.drop_table(safe, **options)
