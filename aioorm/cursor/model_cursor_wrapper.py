import collections
from aioorm.reflect import is_model
from aioorm.ast.column import Column
from aioorm.ast.node import Node
from aioorm.ast.function import Function
from aioorm.ast.join import JOIN
from aioorm.ast.entity import Entity
from aioorm.fields.field import Field, FieldAlias
from aioorm.model.model import Model
from .cursor_wrapper import DictCursorWrapper


class BaseModelCursorWrapper(DictCursorWrapper):
    def __init__(self, cursor, model, columns):
        super(BaseModelCursorWrapper, self).__init__(cursor)
        self.model = model
        self.select = columns or []

    def _initialize_columns(self):
        combined = self.model._meta.combined
        table = self.model._meta.table
        description = self.cursor.description

        self.ncols = len(self.cursor.description)
        self.columns = []
        self.converters = converters = [None] * self.ncols
        self.fields = fields = [None] * self.ncols

        for idx, description_item in enumerate(description):
            column = description_item[0]
            dot_index = column.find('.')
            if dot_index != -1:
                column = column[dot_index + 1:]

            self.columns.append(column)
            try:
                node = self.select[idx]
            except IndexError:
                continue
            else:
                node = node.unwrap()

            # Heuristics used to attempt to get the field associated with a
            # given SELECT column, so that we can accurately convert the value
            # returned by the database-cursor into a Python object.
            if isinstance(node, Field):
                converters[idx] = node.python_value
                fields[idx] = node
                if column == node.name or column == node.column_name:
                    self.columns[idx] = node.name
            elif column in combined:
                if not (isinstance(node, Function) and not node._coerce):
                    # Unlikely, but if a function was aliased to a column,
                    # don't use that column's converter if coerce is False.
                    converters[idx] = combined[column].python_value
                if isinstance(node, Column) and node.source == table:
                    fields[idx] = combined[column]
            elif (isinstance(node, Function) and node.arguments and
                  node._coerce):
                # Try to special-case functions calling fields.
                first = node.arguments[0]
                if isinstance(first, Node):
                    first = first.unwrap()

                if isinstance(first, Field):
                    converters[idx] = first.python_value
                elif isinstance(first, Entity):
                    path = first._path[-1]
                    field = combined.get(path)
                    if field is not None:
                        converters[idx] = field.python_value

    initialize = _initialize_columns

    def process_row(self, row):
        raise NotImplementedError


class ModelDictCursorWrapper(BaseModelCursorWrapper):
    def process_row(self, row):
        result = {}
        columns, converters = self.columns, self.converters
        fields = self.fields

        for i in range(self.ncols):
            attr = columns[i]
            if converters[i] is not None:
                result[attr] = converters[i](row[i])
            else:
                result[attr] = row[i]

        return result


class ModelTupleCursorWrapper(ModelDictCursorWrapper):
    constructor = tuple

    def process_row(self, row):
        columns, converters = self.columns, self.converters
        return self.constructor([
            (converters[i](row[i]) if converters[i] is not None else row[i])
            for i in range(self.ncols)])


class ModelNamedTupleCursorWrapper(ModelTupleCursorWrapper):
    def initialize(self):
        self._initialize_columns()
        attributes = []
        for i in range(self.ncols):
            attributes.append(self.columns[i])
        self.tuple_class = collections.namedtuple('Row', attributes)
        self.constructor = lambda row: self.tuple_class(*row)


class ModelObjectCursorWrapper(ModelDictCursorWrapper):
    def __init__(self, cursor, model, select, constructor):
        self.constructor = constructor
        self.is_model = is_model(constructor)
        super(ModelObjectCursorWrapper, self).__init__(cursor, model, select)

    def process_row(self, row):
        data = super(ModelObjectCursorWrapper, self).process_row(row)
        if self.is_model:
            # Clear out any dirty fields before returning to the user.
            obj = self.constructor(__no_default__=1, **data)
            obj._dirty.clear()
            return obj
        else:
            return self.constructor(**data)


class ModelCursorWrapper(BaseModelCursorWrapper):
    def __init__(self, cursor, model, select, from_list, joins):
        super(ModelCursorWrapper, self).__init__(cursor, model, select)
        self.from_list = from_list
        self.joins = joins

    def initialize(self):
        self._initialize_columns()
        selected_src = set([field.model for field in self.fields
                            if field is not None])
        select, columns = self.select, self.columns

        self.key_to_constructor = {self.model: self.model}
        self.src_is_dest = {}
        self.src_to_dest = []
        accum = collections.deque(self.from_list)
        dests = set()
        while accum:
            curr = accum.popleft()
            if isinstance(curr, Join):
                accum.append(curr.lhs)
                accum.append(curr.rhs)
                continue

            if curr not in self.joins:
                continue

            for key, attr, constructor in self.joins[curr]:
                if key not in self.key_to_constructor:
                    self.key_to_constructor[key] = constructor
                    self.src_to_dest.append((curr, attr, key,
                                             isinstance(curr, dict)))
                    dests.add(key)
                    accum.append(key)

        for src, _, dest, _ in self.src_to_dest:
            self.src_is_dest[src] = src in dests and (dest in selected_src
                                                      or src in selected_src)

        self.column_keys = []
        for idx, node in enumerate(select):
            key = self.model
            field = self.fields[idx]
            if field is not None:
                if isinstance(field, FieldAlias):
                    key = field.source
                else:
                    key = field.model
            else:
                if isinstance(node, Node):
                    node = node.unwrap()
                if isinstance(node, Column):
                    key = node.source

            self.column_keys.append(key)

    def process_row(self, row):
        objects = {}
        object_list = []
        for key, constructor in self.key_to_constructor.items():
            objects[key] = constructor(__no_default__=True)
            object_list.append(objects[key])

        set_keys = set()
        for idx, key in enumerate(self.column_keys):
            instance = objects[key]
            if self.fields[idx] is not None:
                column = self.fields[idx].name
            else:
                column = self.columns[idx]
            value = row[idx]
            if value is not None:
                set_keys.add(key)
            if self.converters[idx]:
                value = self.converters[idx](value)

            if isinstance(instance, dict):
                instance[column] = value
            else:
                setattr(instance, column, value)

        # Need to do some analysis on the joins before this.
        for (src, attr, dest, is_dict) in self.src_to_dest:
            instance = objects[src]
            try:
                joined_instance = objects[dest]
            except KeyError:
                continue

            # If no fields were set on the destination instance then do not
            # assign an "empty" instance.
            if instance is None or dest is None or (
                    dest not in set_keys and not self.src_is_dest.get(dest)):
                continue

            if is_dict:
                instance[attr] = joined_instance
            else:
                setattr(instance, attr, joined_instance)

        # When instantiating models from a cursor, we clear the dirty fields.
        for instance in object_list:
            if isinstance(instance, Model):
                instance._dirty.clear()

        return objects[self.model]
