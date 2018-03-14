from aioorm.utils import _callable_context_manager, with_metaclass, __deprecated__
from aioorm.ast.node import Node
from aioorm.fields.field import Field
from aioorm.error import DoesNotExist, IntegrityError
from .module_meta import ModelBase
from .model_alias import ModelAlias


class _BoundModelsContext(_callable_context_manager):
    def __init__(self, models, database, bind_refs, bind_backrefs):
        self.models = models
        self.database = database
        self.bind_refs = bind_refs
        self.bind_backrefs = bind_backrefs

    def __enter__(self):
        self._orig_database = []
        for model in self.models:
            self._orig_database.append(model._meta.database)
            model.bind(self.database, self.bind_refs, self.bind_backrefs)
        return self.models

    def __exit__(self, exc_type, exc_val, exc_tb):
        for model, db in zip(self.models, self._orig_database):
            model.bind(db, self.bind_refs, self.bind_backrefs)


class Model(with_metaclass(ModelBase, Node)):
    def __init__(self, *args, **kwargs):
        if kwargs.pop('__no_default__', None):
            self.__data__ = {}
        else:
            self.__data__ = self._meta.get_default_dict()
        self._dirty = set(self.__data__)
        self.__rel__ = {}

        for k in kwargs:
            setattr(self, k, kwargs[k])

    @classmethod
    def validate_model(cls):
        pass

    @classmethod
    def alias(cls, alias=None):
        return ModelAlias(cls, alias)

    @classmethod
    def select(cls, *fields):
        is_default = not fields
        if not fields:
            fields = cls._meta.sorted_fields
        return ModelSelect(cls, fields, is_default=is_default)

    @classmethod
    def _normalize_data(cls, data, kwargs):
        normalized = {}
        if data:
            if not isinstance(data, dict):
                if kwargs:
                    raise ValueError('Data cannot be mixed with keyword '
                                     'arguments: %s' % data)
                return data
            for key in data:
                try:
                    field = (key if isinstance(key, Field)
                             else cls._meta.combined[key])
                except KeyError:
                    raise ValueError('Unrecognized field name: "%s" in %s.' %
                                     (key, data))
                normalized[field] = data[key]
        if kwargs:
            for key in kwargs:
                try:
                    normalized[cls._meta.combined[key]] = kwargs[key]
                except KeyError:
                    normalized[getattr(cls, key)] = kwargs[key]
        return normalized

    @classmethod
    def update(cls, __data=None, **update):
        return ModelUpdate(cls, cls._normalize_data(__data, update))

    @classmethod
    def insert(cls, __data=None, **insert):
        return ModelInsert(cls, cls._normalize_data(__data, insert))

    @classmethod
    def insert_many(cls, rows, fields=None):
        return ModelInsert(cls, insert=rows, columns=fields)

    @classmethod
    def insert_from(cls, query, fields):
        columns = [getattr(cls, field) if isinstance(field, basestring)
                   else field for field in fields]
        return ModelInsert(cls, insert=query, columns=columns)

    @classmethod
    def replace(cls, __data=None, **insert):
        return cls.insert(__data, **insert).on_conflict('REPLACE')

    @classmethod
    def replace_many(cls, rows, fields=None):
        return (cls
                .insert_many(rows=rows, fields=fields)
                .on_conflict('REPLACE'))

    @classmethod
    def raw(cls, sql, *params):
        return ModelRaw(cls, sql, params)

    @classmethod
    def delete(cls):
        return ModelDelete(cls)

    @classmethod
    def create(cls, **query):
        inst = cls(**query)
        inst.save(force_insert=True)
        return inst

    @classmethod
    def noop(cls):
        return NoopModelSelect(cls, ())

    @classmethod
    def get(cls, *query, **filters):
        sq = cls.select()
        if query:
            sq = sq.where(*query)
        if filters:
            sq = sq.filter(**filters)
        return sq.get()

    @classmethod
    def get_or_none(cls, *query, **filters):
        try:
            return cls.get(*query, **filters)
        except DoesNotExist:
            pass

    @classmethod
    def get_by_id(cls, pk):
        return cls.get(cls._meta.primary_key == pk)

    @classmethod
    def set_by_id(cls, key, value):
        if key is None:
            return cls.insert(value).execute()
        else:
            return (cls.update(value)
                    .where(cls._meta.primary_key == key).execute())

    @classmethod
    def delete_by_id(cls, pk):
        return cls.delete().where(cls._meta.primary_key == pk).execute()

    @classmethod
    def get_or_create(cls, **kwargs):
        defaults = kwargs.pop('defaults', {})
        query = cls.select()
        for field, value in kwargs.items():
            query = query.where(getattr(cls, field) == value)

        try:
            return query.get(), False
        except cls.DoesNotExist:
            try:
                if defaults:
                    kwargs.update(defaults)
                with cls._meta.database.atomic():
                    return cls.create(**kwargs), True
            except IntegrityError as exc:
                try:
                    return query.get(), False
                except cls.DoesNotExist:
                    raise exc

    @classmethod
    def filter(cls, *dq_nodes, **filters):
        return cls.select().filter(*dq_nodes, **filters)

    def get_id(self):
        return getattr(self, self._meta.primary_key.name)

    _pk = property(get_id)

    @_pk.setter
    def _pk(self, value):
        setattr(self, self._meta.primary_key.name, value)

    def _pk_expr(self):
        return self._meta.primary_key == self._pk

    def _prune_fields(self, field_dict, only):
        new_data = {}
        for field in only:
            if isinstance(field, str):
                field = self._meta.combined[field]
            if field.name in field_dict:
                new_data[field.name] = field_dict[field.name]
        return new_data

    def _populate_unsaved_relations(self, field_dict):
        for foreign_key_field in self._meta.refs:
            foreign_key = foreign_key_field.name
            conditions = (
                foreign_key in field_dict and
                field_dict[foreign_key] is None and
                self.__rel__.get(foreign_key) is not None)
            if conditions:
                setattr(self, foreign_key, getattr(self, foreign_key))
                field_dict[foreign_key] = self.__data__[foreign_key]

    def save(self, force_insert=False, only=None):
        field_dict = self.__data__.copy()
        if self._meta.primary_key is not False:
            pk_field = self._meta.primary_key
            pk_value = self._pk
        else:
            pk_field = pk_value = None
        if only:
            field_dict = self._prune_fields(field_dict, only)
        elif self._meta.only_save_dirty and not force_insert:
            field_dict = self._prune_fields(field_dict, self.dirty_fields)
            if not field_dict:
                self._dirty.clear()
                return False

        self._populate_unsaved_relations(field_dict)
        if pk_value is not None and not force_insert:
            if self._meta.composite_key:
                for pk_part_name in pk_field.field_names:
                    field_dict.pop(pk_part_name, None)
            else:
                field_dict.pop(pk_field.name, None)
            rows = self.update(**field_dict).where(self._pk_expr()).execute()
        elif pk_field is None or not self._meta.auto_increment:
            self.insert(**field_dict).execute()
            rows = 1
        else:
            pk_from_cursor = self.insert(**field_dict).execute()
            if pk_from_cursor is not None:
                pk_value = pk_from_cursor
            self._pk = pk_value
            rows = 1
        self._dirty.clear()
        return rows

    def is_dirty(self):
        return bool(self._dirty)

    @property
    def dirty_fields(self):
        return [f for f in self._meta.sorted_fields if f.name in self._dirty]

    def dependencies(self, search_nullable=False):
        model_class = type(self)
        query = self.select(self._meta.primary_key).where(self._pk_expr())
        stack = [(type(self), query)]
        seen = set()

        while stack:
            klass, query = stack.pop()
            if klass in seen:
                continue
            seen.add(klass)
            for fk, rel_model in klass._meta.backrefs.items():
                if rel_model is model_class:
                    node = (fk == self.__data__[fk.rel_field.name])
                else:
                    node = fk << query
                subquery = (rel_model.select(rel_model._meta.primary_key)
                            .where(node))
                if not fk.null or search_nullable:
                    stack.append((rel_model, subquery))
                yield (node, fk)

    def delete_instance(self, recursive=False, delete_nullable=False):
        if recursive:
            dependencies = self.dependencies(delete_nullable)
            for query, fk in reversed(list(dependencies)):
                model = fk.model
                if fk.null and not delete_nullable:
                    model.update(**{fk.name: None}).where(query).execute()
                else:
                    model.delete().where(query).execute()
        return self.delete().where(self._pk_expr()).execute()

    def __hash__(self):
        return hash((self.__class__, self._pk))

    def __eq__(self, other):
        return (
            other.__class__ == self.__class__ and
            self._pk is not None and
            other._pk == self._pk)

    def __ne__(self, other):
        return not self == other

    def __sql__(self, ctx):
        return ctx.sql(getattr(self, self._meta.primary_key.name))

    @classmethod
    def bind(cls, database, bind_refs=True, bind_backrefs=True):
        is_different = cls._meta.database is not database
        cls._meta.set_database(database)
        if bind_refs or bind_backrefs:
            G = cls._meta.model_graph(refs=bind_refs, backrefs=bind_backrefs)
            for _, model, is_backref in G:
                model._meta.set_database(database)
        return is_different

    @classmethod
    def bind_ctx(cls, database, bind_refs=True, bind_backrefs=True):
        return _BoundModelsContext((cls,), database, bind_refs, bind_backrefs)

    @classmethod
    def table_exists(cls):
        meta = cls._meta
        return meta.database.table_exists(meta.table, meta.schema)

    @classmethod
    def create_table(cls, safe=True, **options):
        if 'fail_silently' in options:
            __deprecated__('"fail_silently" has been deprecated in favor of '
                           '"safe" for the create_table() method.')
            safe = options.pop('fail_silently')

        if safe and not cls._meta.database.safe_create_index \
           and cls.table_exists():
            return
        cls._schema.create_all(safe, **options)

    @classmethod
    def drop_table(cls, safe=True, **options):
        if safe and not cls._meta.database.safe_drop_index \
           and not cls.table_exists():
            return
        cls._schema.drop_all(safe, **options)

    @classmethod
    def index(cls, *fields, **kwargs):
        return ModelIndex(cls, fields, **kwargs)

    @classmethod
    def add_index(cls, *fields, **kwargs):
        if len(fields) == 1 and isinstance(fields[0], (SQL, Index)):
            cls._meta.indexes.append(fields[0])
        else:
            cls._meta.indexes.append(ModelIndex(cls, fields, **kwargs))
