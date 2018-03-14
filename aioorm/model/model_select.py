import collections
import operator
from functools import reduce
from aioorm.const import ROW, DJANGO_MAP, OP
from aioorm.utils import prefetch
from aioorm.ast.dq import DQ
from aioorm.ast.node import Node
from aioorm.ast.table import Table
from aioorm.ast.entity import Alias, Expression, Negated, CommaNodeList
from aioorm.ast.column import Column, ColumnBase
from aioorm.reflect import is_model
from aioorm.fields.accessor import BackrefAccessor
from aioorm.fields.field import Field
from aioorm.fields.foreignkey_fields import ForeignKeyField
from aioorm.query.select import CompoundSelectQuery, Select
from .model_query_helper import _ModelQueryHelper
from .model_alias import ModelAlias


class BaseModelSelect(_ModelQueryHelper):
    def __add__(self, rhs):
        return ModelCompoundSelectQuery(self.model, self, 'UNION ALL', rhs)

    def __or__(self, rhs):
        return ModelCompoundSelectQuery(self.model, self, 'UNION', rhs)

    def __and__(self, rhs):
        return ModelCompoundSelectQuery(self.model, self, 'INTERSECT', rhs)

    def __sub__(self, rhs):
        return ModelCompoundSelectQuery(self.model, self, 'EXCEPT', rhs)

    def __iter__(self):
        if not self._cursor_wrapper:
            self.execute()
        return iter(self._cursor_wrapper)

    def prefetch(self, *subqueries):
        return prefetch(self, *subqueries)

    def get(self):
        clone = self.paginate(1, 1)
        clone._cursor_wrapper = None
        try:
            return clone.execute()[0]
        except IndexError:
            sql, params = clone.sql()
            raise self.model.DoesNotExist('%s instance matching query does '
                                          'not exist:\nSQL: %s\nParams: %s' %
                                          (clone.model, sql, params))

    @Node.copy
    def group_by(self, *columns):
        grouping = []
        for column in columns:
            if is_model(column):
                grouping.extend(column._meta.sorted_fields)
            elif isinstance(column, Table):
                if not column._columns:
                    raise ValueError('Cannot pass a table to group_by() that '
                                     'does not have columns explicitly '
                                     'declared.')
                grouping.extend([getattr(column, col_name)
                                 for col_name in column._columns])
            else:
                grouping.append(column)
        self._group_by = grouping


class ModelCompoundSelectQuery(BaseModelSelect, CompoundSelectQuery):
    def __init__(self, model, *args, **kwargs):
        self.model = model
        super(ModelCompoundSelectQuery, self).__init__(*args, **kwargs)


class ModelSelect(BaseModelSelect, Select):
    def __init__(self, model, fields_or_models, is_default=False):
        self.model = self._join_ctx = model
        self._joins = {}
        self._is_default = is_default
        fields = []
        for fm in fields_or_models:
            if is_model(fm):
                fields.extend(fm._meta.sorted_fields)
            elif isinstance(fm, ModelAlias):
                fields.extend(fm.get_field_aliases())
            elif isinstance(fm, Table) and fm._columns:
                fields.extend([getattr(fm, col) for col in fm._columns])
            else:
                fields.append(fm)
        super(ModelSelect, self).__init__([model], fields)

    def select(self, *fields):
        if fields or not self._is_default:
            return super(ModelSelect, self).select(*fields)
        return self

    def switch(self, ctx=None):
        self._join_ctx = ctx
        return self

    @Node.copy
    def objects(self, constructor=None):
        self._row_type = ROW.CONSTRUCTOR
        self._constructor = self.model if constructor is None else constructor

    def _get_model(self, src):
        if is_model(src):
            return src, True
        elif isinstance(src, Table) and src._model:
            return src._model, False
        elif isinstance(src, ModelAlias):
            return src.model, False
        elif isinstance(src, ModelSelect):
            return src.model, False
        return None, False

    def _normalize_join(self, src, dest, on, attr):
        # Allow "on" expression to have an alias that determines the
        # destination attribute for the joined data.
        on_alias = isinstance(on, Alias)
        if on_alias:
            attr = on._alias
            on = on.alias()

        src_model, src_is_model = self._get_model(src)
        dest_model, dest_is_model = self._get_model(dest)
        if src_model and dest_model:
            self._join_ctx = dest
            constructor = dest_model

            if not (src_is_model and dest_is_model) and isinstance(on, Column):
                if on.source is src:
                    to_field = src_model._meta.columns[on.name]
                elif on.source is dest:
                    to_field = dest_model._meta.columns[on.name]
                else:
                    raise AttributeError('"on" clause Column %s does not '
                                         'belong to %s or %s.' %
                                         (on, src_model, dest_model))
                on = None
            elif isinstance(on, Field):
                to_field = on
                on = None
            else:
                to_field = None

            fk_field, is_backref = self._generate_on_clause(
                src_model, dest_model, to_field, on)

            if on is None:
                src_attr = 'name' if src_is_model else 'column_name'
                dest_attr = 'name' if dest_is_model else 'column_name'
                if is_backref:
                    lhs = getattr(dest, getattr(fk_field, dest_attr))
                    rhs = getattr(src, getattr(fk_field.rel_field, src_attr))
                else:
                    lhs = getattr(src, getattr(fk_field, src_attr))
                    rhs = getattr(dest, getattr(fk_field.rel_field, dest_attr))
                on = (lhs == rhs)

            if not attr:
                if fk_field is not None and not is_backref:
                    attr = fk_field.name
                else:
                    attr = dest_model._meta.name

        elif isinstance(dest, Source):
            constructor = dict
            attr = attr or dest._alias
            if not attr and isinstance(dest, Table):
                attr = attr or dest.__name__

        return (on, attr, constructor)

    @Node.copy
    def join(self, dest, join_type='INNER', on=None, src=None, attr=None):
        src = self._join_ctx if src is None else src

        on, attr, constructor = self._normalize_join(src, dest, on, attr)
        if attr:
            self._joins.setdefault(src, [])
            self._joins[src].append((dest, attr, constructor))

        return super(ModelSelect, self).join(dest, join_type, on)

    @Node.copy
    def join_from(self, src, dest, join_type='INNER', on=None, attr=None):
        return self.join(dest, join_type, on, src, attr)

    def _generate_on_clause(self, src, dest, to_field=None, on=None):
        meta = src._meta
        backref = fk_fields = False
        if dest in meta.model_refs:
            fk_fields = meta.model_refs[dest]
        elif dest in meta.model_backrefs:
            fk_fields = meta.model_backrefs[dest]
            backref = True

        if not fk_fields:
            if on is not None:
                return None, False
            raise ValueError('Unable to find foreign key between %s and %s. '
                             'Please specify an explicit join condition.' %
                             (src, dest))
        if to_field is not None:
            target = (to_field.field if isinstance(to_field, FieldAlias)
                      else to_field)
            fk_fields = [f for f in fk_fields if (
                         (f is target) or
                         (backref and f.rel_field is to_field))]

        if len(fk_fields) > 1:
            if on is None:
                raise ValueError('More than one foreign key between %s and %s.'
                                 ' Please specify which you are joining on.' %
                                 (src, dest))
            return None, False
        else:
            fk_field = fk_fields[0]

        return fk_field, backref

    def _get_model_cursor_wrapper(self, cursor):
        if len(self._from_list) == 1 and not self._joins:
            return ModelObjectCursorWrapper(cursor, self.model,
                                            self._returning, self.model)
        return ModelCursorWrapper(cursor, self.model, self._returning,
                                  self._from_list, self._joins)

    def ensure_join(self, lm, rm, on=None, **join_kwargs):
        join_ctx = self._join_ctx
        for dest, attr, constructor in self._joins.get(lm, []):
            if dest == rm:
                return self
        return self.switch(lm).join(rm, on=on, **join_kwargs).switch(join_ctx)

    def convert_dict_to_node(self, qdict):
        accum = []
        joins = []
        fks = (ForeignKeyField, BackrefAccessor)
        for key, value in sorted(qdict.items()):
            curr = self.model
            if '__' in key and key.rsplit('__', 1)[1] in DJANGO_MAP:
                key, op = key.rsplit('__', 1)
                op = DJANGO_MAP[op]
            elif value is None:
                op = OP.IS
            else:
                op = OP.EQ

            if '__' not in key:
                # Handle simplest case. This avoids joining over-eagerly when a
                # direct FK lookup is all that is required.
                model_attr = getattr(curr, key)
            else:
                for piece in key.split('__'):
                    for dest, attr, _ in self._joins.get(curr, ()):
                        if attr == piece or (isinstance(dest, ModelAlias) and
                                             dest.alias == piece):
                            curr = dest
                            break
                    else:
                        model_attr = getattr(curr, piece)
                        if value is not None and isinstance(model_attr, fks):
                            curr = model_attr.rel_model
                            joins.append(model_attr)
            accum.append(Expression(model_attr, op, value))
        return accum, joins

    def filter(self, *args, **kwargs):
        # normalize args and kwargs into a new expression
        dq_node = ColumnBase()
        if args:
            dq_node &= reduce(operator.and_, [a.clone() for a in args])
        if kwargs:
            dq_node &= DQ(**kwargs)

        # dq_node should now be an Expression, lhs = Node(), rhs = ...
        q = collections.deque([dq_node])
        dq_joins = set()
        while q:
            curr = q.popleft()
            if not isinstance(curr, Expression):
                continue
            for side, piece in (('lhs', curr.lhs), ('rhs', curr.rhs)):
                if isinstance(piece, DQ):
                    query, joins = self.convert_dict_to_node(piece.query)
                    dq_joins.update(joins)
                    expression = reduce(operator.and_, query)
                    # Apply values from the DQ object.
                    if piece._negated:
                        expression = Negated(expression)
                    #expression._alias = piece._alias
                    setattr(curr, side, expression)
                else:
                    q.append(piece)

        dq_node = dq_node.rhs

        query = self.clone()
        for field in dq_joins:
            if isinstance(field, ForeignKeyField):
                lm, rm = field.model, field.rel_model
                field_obj = field
            elif isinstance(field, BackrefAccessor):
                lm, rm = field.model, field.rel_model
                field_obj = field.field
            query = query.ensure_join(lm, rm, field_obj)
        return query.where(dq_node)

    def __sql_selection__(self, ctx, is_subquery=False):
        if self._is_default and is_subquery and len(self._returning) > 1 and \
           self.model._meta.primary_key is not False:
            return ctx.sql(self.model._meta.primary_key)

        return ctx.sql(CommaNodeList(self._returning))


class NoopModelSelect(ModelSelect):
    def __sql__(self, ctx):
        return self.model._meta.database.get_noop_select(ctx)

    def _get_cursor_wrapper(self, cursor):
        return CursorWrapper(cursor)
