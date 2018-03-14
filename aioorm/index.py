import re
import hashlib
import operator
from functools import reduce
from aioorm.ast.node import Node
from aioorm.ast.entity import Entity, EnclosedNodeList, SQL
from aioorm.ast.table import Table


class Index(Node):
    def __init__(self, name, table, expressions, unique=False, safe=False,
                 where=None, using=None):
        self._name = name
        self._table = Entity(table) if not isinstance(table, Table) else table
        self._expressions = expressions
        self._where = where
        self._unique = unique
        self._safe = safe
        self._using = using

    @Node.copy
    def safe(self, _safe=True):
        self._safe = _safe

    @Node.copy
    def where(self, *expressions):
        if self._where is not None:
            expressions = (self._where,) + expressions
        self._where = reduce(operator.and_, expressions)

    @Node.copy
    def using(self, _using=None):
        self._using = _using

    def __sql__(self, ctx):
        statement = 'CREATE UNIQUE INDEX ' if self._unique else 'CREATE INDEX '
        with ctx.scope_values(subquery=True):
            ctx.literal(statement)
            if self._safe:
                ctx.literal('IF NOT EXISTS ')
            (ctx
             .sql(Entity(self._name))
             .literal(' ON ')
             .sql(self._table)
             .literal(' '))
            if self._using is not None:
                ctx.literal('USING %s ' % self._using)

            ctx.sql(EnclosedNodeList([
                SQL(expr) if isinstance(expr, str) else expr
                for expr in self._expressions]))
            if self._where is not None:
                ctx.literal(' WHERE ').sql(self._where)

        return ctx


class ModelIndex(Index):
    def __init__(self, model, fields, unique=False, safe=True, where=None,
                 using=None, name=None):
        self._model = model
        if name is None:
            name = self._generate_name_from_fields(model, fields)
        if using is None:
            for field in fields:
                if getattr(field, 'index_type', None):
                    using = field.index_type
        super(ModelIndex, self).__init__(
            name=name,
            table=model._meta.table,
            expressions=fields,
            unique=unique,
            safe=safe,
            where=where,
            using=using)

    def _generate_name_from_fields(self, model, fields):
        accum = []
        for field in fields:
            if isinstance(field, str):
                accum.append(field.split()[0])
            else:
                if isinstance(field, Node) and not isinstance(field, Field):
                    field = field.unwrap()
                if isinstance(field, Field):
                    accum.append(field.column_name)

        if not accum:
            raise ValueError('Unable to generate a name for the index, please '
                             'explicitly specify a name.')

        index_name = re.sub('[^\w]+', '',
                            '%s_%s' % (model._meta.name, '_'.join(accum)))
        if len(index_name) > 64:
            index_hash = hashlib.md5(index_name.encode('utf-8')).hexdigest()
            index_name = '%s_%s' % (index_name[:56], index_hash[:7])
        return index_name
