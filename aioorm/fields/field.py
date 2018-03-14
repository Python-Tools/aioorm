from aioorm.ast.entity import ColumnBase, Entity, SQL, NodeList
from aioorm.ast.column import Column
from aioorm.utils import __deprecated__
from .accessor import FieldAccessor


class Field(ColumnBase):
    _field_counter = 0
    _order = 0
    accessor_class = FieldAccessor
    auto_increment = False
    field_type = 'DEFAULT'

    def __init__(self, null=False, index=False, unique=False, column_name=None,
                 default=None, primary_key=False, constraints=None,
                 sequence=None, collation=None, unindexed=False, choices=None,
                 help_text=None, verbose_name=None, db_column=None,
                 _hidden=False):
        if db_column is not None:
            __deprecated__('"db_column" has been deprecated in favor of '
                           '"column_name" for Field objects.')
            column_name = db_column

        self.null = null
        self.index = index
        self.unique = unique
        self.column_name = column_name
        self.default = default
        self.primary_key = primary_key
        self.constraints = constraints  # List of column constraints.
        self.sequence = sequence  # Name of sequence, e.g. foo_id_seq.
        self.collation = collation
        self.unindexed = unindexed
        self.choices = choices
        self.help_text = help_text
        self.verbose_name = verbose_name
        self._hidden = _hidden

        # Used internally for recovering the order in which Fields were defined
        # on the Model class.
        Field._field_counter += 1
        self._order = Field._field_counter
        self._sort_key = (self.primary_key and 1 or 2), self._order

    def __hash__(self):
        return hash(self.name + '.' + self.model.__name__)

    def bind(self, model, name, set_attribute=True):
        self.model = model
        self.name = name
        self.column_name = self.column_name or name
        if set_attribute:
            setattr(model, name, self.accessor_class(model, self, name))

    @property
    def column(self):
        return Column(self.model._meta.table, self.column_name)

    def coerce(self, value):
        return value

    def db_value(self, value):
        return value if value is None else self.coerce(value)

    def python_value(self, value):
        return value if value is None else self.coerce(value)

    def get_sort_key(self, ctx):
        return self._sort_key

    def __sql__(self, ctx):
        return ctx.sql(self.column)

    def get_modifiers(self):
        return

    def ddl_datatype(self, ctx):
        if ctx and ctx.state.field_types:
            column_type = ctx.state.field_types.get(self.field_type,
                                                    self.field_type)
        else:
            column_type = self.field_type

        modifiers = self.get_modifiers()
        if column_type and modifiers:
            modifier_literal = ', '.join([str(m) for m in modifiers])
            return SQL('%s(%s)' % (column_type, modifier_literal))
        else:
            return SQL(column_type)

    def ddl(self, ctx):
        accum = [Entity(self.column_name)]
        data_type = self.ddl_datatype(ctx)
        if data_type:
            accum.append(data_type)
        if self.unindexed:
            accum.append(SQL('UNINDEXED'))
        if not self.null:
            accum.append(SQL('NOT NULL'))
        if self.primary_key:
            accum.append(SQL('PRIMARY KEY'))
        if self.sequence:
            accum.append(SQL("DEFAULT NEXTVAL('%s')" % self.sequence))
        if self.constraints:
            accum.extend(self.constraints)
        if self.collation:
            accum.append(SQL('COLLATE %s' % self.collation))
        return NodeList(accum)
