import re
import collections
from aioorm.utils import __deprecated__
from aioorm.fields.utils import _SortedFieldList
from aioorm.fields.meta_fields import MetaField
from aioorm.fields.foreignkey_fields import ForeignKeyField
from aioorm.fields.composite_key import CompositeKey
from aioorm.fields.many2many_fields import ManyToManyField
from aioorm.ast.table import Table
from aioorm.ast.entity import Entity
from aioorm.ast.node import Node


class Metadata(object):
    def __init__(self, model, database=None, table_name=None, indexes=None,
                 primary_key=None, constraints=None, schema=None,
                 only_save_dirty=False, table_alias=None, depends_on=None,
                 options=None, db_table=None, table_function=None,
                 without_rowid=False, **kwargs):
        if db_table is not None:
            __deprecated__('"db_table" has been deprecated in favor of '
                           '"table_name" for Models.')
            table_name = db_table
        self.model = model
        self.database = database

        self.fields = {}
        self.columns = {}
        self.combined = {}

        self._sorted_field_list = _SortedFieldList()
        self.sorted_fields = []
        self.sorted_field_names = []

        self.defaults = {}
        self._default_by_name = {}
        self._default_dict = {}
        self._default_callables = {}
        self._default_callable_list = []

        self.name = model.__name__.lower()
        self.table_function = table_function
        if not table_name:
            table_name = (self.table_function(model)
                          if self.table_function
                          else re.sub('[^\w]+', '_', self.name))
        self.table_name = table_name
        self._table = None

        self.indexes = list(indexes) if indexes else []
        self.constraints = constraints
        self._schema = schema
        self.primary_key = primary_key
        self.composite_key = self.auto_increment = None
        self.only_save_dirty = only_save_dirty
        self.table_alias = table_alias
        self.depends_on = depends_on
        self.without_rowid = without_rowid

        self.refs = {}
        self.backrefs = {}
        self.model_refs = collections.defaultdict(list)
        self.model_backrefs = collections.defaultdict(list)
        self.manytomany = {}

        self.options = options or {}
        for key, value in kwargs.items():
            setattr(self, key, value)
        self._additional_keys = set(kwargs.keys())

    def model_graph(self, refs=True, backrefs=True, depth_first=True):
        if not refs and not backrefs:
            raise ValueError('One of `refs` or `backrefs` must be True.')

        accum = [(None, self.model, None)]
        seen = set()
        queue = collections.deque((self,))
        method = queue.pop if depth_first else queue.popleft

        while queue:
            curr = method()
            if curr in seen:
                continue
            seen.add(curr)

            if refs:
                for fk, model in curr.refs.items():
                    accum.append((fk, model, False))
                    queue.append(model._meta)
            if backrefs:
                for fk, model in curr.backrefs.items():
                    accum.append((fk, model, True))
                    queue.append(model._meta)

        return accum

    def add_ref(self, field):
        rel = field.rel_model
        self.refs[field] = rel
        self.model_refs[rel].append(field)
        rel._meta.backrefs[field] = self.model
        rel._meta.model_backrefs[self.model].append(field)

    def remove_ref(self, field):
        rel = field.rel_model
        del self.refs[field]
        self.model_ref[rel].remove(field)
        del rel._meta.backrefs[field]
        rel._meta.model_backrefs[self.model].remove(field)

    def add_manytomany(self, field):
        self.manytomany[field.name] = field

    def remove_manytomany(self, field):
        del self.manytomany[field.name]

    @property
    def table(self):
        if self._table is None:
            self._table = Table(
                self.table_name,
                [field.column_name for field in self.sorted_fields],
                schema=self.schema,
                alias=self.table_alias,
                _model=self.model,
                _database=self.database)
        return self._table

    @table.setter
    def table(self, value):
        raise AttributeError('Cannot set the "table".')

    @table.deleter
    def table(self):
        self._table = None

    @property
    def schema(self):
        return self._schema

    @schema.setter
    def schema(self, value):
        self._schema = value
        del self.table

    @property
    def entity(self):
        if self._schema:
            return Entity(self._schema, self.table_name)
        else:
            return Entity(self.table_name)

    def _update_sorted_fields(self):
        self.sorted_fields = list(self._sorted_field_list)
        self.sorted_field_names = [f.name for f in self.sorted_fields]

    def add_field(self, field_name, field, set_attribute=True):
        if field_name in self.fields:
            self.remove_field(field_name)
        elif field_name in self.manytomany:
            self.remove_manytomany(self.manytomany[field_name])

        if not isinstance(field, MetaField):
            del self.table
            field.bind(self.model, field_name, set_attribute)
            self.fields[field.name] = field
            self.columns[field.column_name] = field
            self.combined[field.name] = field
            self.combined[field.column_name] = field

            self._sorted_field_list.insert(field)
            self._update_sorted_fields()

            if field.default is not None:
                # This optimization helps speed up model instance construction.
                self.defaults[field] = field.default
                if callable(field.default):
                    self._default_callables[field] = field.default
                    self._default_callable_list.append((field.name,
                                                        field.default))
                else:
                    self._default_dict[field] = field.default
                    self._default_by_name[field.name] = field.default
        else:
            field.bind(self.model, field_name, set_attribute)

        if isinstance(field, ForeignKeyField):
            self.add_ref(field)
        elif isinstance(field, ManyToManyField):
            self.add_manytomany(field)

    def remove_field(self, field_name):
        if field_name not in self.fields:
            return

        del self.table
        original = self.fields.pop(field_name)
        del self.columns[original.column_name]
        del self.combined[field_name]
        try:
            del self.combined[original.column_name]
        except KeyError:
            pass
        self._sorted_field_list.remove(original)
        self._update_sorted_fields()

        if original.default is not None:
            del self.defaults[original]
            if self._default_callables.pop(original, None):
                for i, (name, _) in enumerate(self._default_callable_list):
                    if name == field_name:
                        self._default_callable_list.pop(i)
                        break
            else:
                self._default_dict.pop(original, None)
                self._default_by_name.pop(original.name, None)

        if isinstance(original, ForeignKeyField):
            self.remove_ref(original)

    def set_primary_key(self, name, field):
        self.composite_key = isinstance(field, CompositeKey)
        self.add_field(name, field)
        self.primary_key = field
        self.auto_increment = (
            field.auto_increment or
            bool(field.sequence))

    def get_primary_keys(self):
        if self.composite_key:
            return tuple([self.fields[field_name]
                          for field_name in self.primary_key.field_names])
        else:
            return (self.primary_key,) if self.primary_key is not False else ()

    def get_default_dict(self):
        dd = self._default_by_name.copy()
        for field_name, default in self._default_callable_list:
            dd[field_name] = default()
        return dd

    def fields_to_index(self):
        indexes = []
        for f in self.sorted_fields:
            if f.primary_key:
                continue
            if f.index or f.unique or isinstance(f, ForeignKeyField):
                indexes.append(ModelIndex(self.model, (f,), unique=f.unique))

        for index_obj in self.indexes:
            if isinstance(index_obj, Node):
                indexes.append(index_obj)
            elif isinstance(index_obj, (list, tuple)):
                index_parts, unique = index_obj
                fields = []
                for part in index_parts:
                    if isinstance(part, str):
                        fields.append(self.combined[part])
                    elif isinstance(part, Node):
                        fields.append(part)
                    else:
                        raise ValueError('Expected either a field name or a '
                                         'subclass of Node. Got: %s' % part)
                indexes.append(ModelIndex(self.model, fields, unique=unique))

        return indexes

    def set_database(self, database):
        self.database = database
        self.model._schema._database = database


class SubclassAwareMetadata(Metadata):
    models = []

    def __init__(self, model, *args, **kwargs):
        super(SubclassAwareMetadata, self).__init__(model, *args, **kwargs)
        self.models.append(model)

    def map_models(self, fn):
        for model in self.models:
            fn(model)
