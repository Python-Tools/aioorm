"""包含ColumnBase, Expression, StringExpression,
SQL,Check,NodeList,CommaNodeList,EnclosedNodeList,Tuple,WrappedNode,BitwiseMixin,
BitwiseNegated,Negated,Ordering,Asc,Desc,Entity,EntityFactory"""
from aioorm.utils import quote
from aioorm.const import OP, SCOPE_SOURCE
from aioorm.sql_generation.context import Context
from .node import Node


class ColumnBase(Node):
    def alias(self, alias):
        if alias:
            return Alias(self, alias)
        return self

    def unalias(self):
        return self

    def cast(self, as_type):
        return Cast(self, as_type)

    def asc(self, collation=None, nulls=None):
        return Asc(self, collation=collation, nulls=nulls)
    __pos__ = asc

    def desc(self, collation=None, nulls=None):
        return Desc(self, collation=collation, nulls=nulls)
    __neg__ = desc

    def __invert__(self):
        return Negated(self)

    def _e(op, inv=False):
        """
        Lightweight factory which returns a method that builds an Expression
        consisting of the left-hand and right-hand operands, using `op`.
        """

        def inner(self, rhs):
            if inv:
                return Expression(rhs, op, self)
            return Expression(self, op, rhs)
        return inner
    __and__ = _e(OP.AND)
    __or__ = _e(OP.OR)

    __add__ = _e(OP.ADD)
    __sub__ = _e(OP.SUB)
    __mul__ = _e(OP.MUL)
    __div__ = __truediv__ = _e(OP.DIV)
    __xor__ = _e(OP.XOR)
    __radd__ = _e(OP.ADD, inv=True)
    __rsub__ = _e(OP.SUB, inv=True)
    __rmul__ = _e(OP.MUL, inv=True)
    __rdiv__ = __rtruediv__ = _e(OP.DIV, inv=True)
    __rand__ = _e(OP.AND, inv=True)
    __ror__ = _e(OP.OR, inv=True)
    __rxor__ = _e(OP.XOR, inv=True)

    def __eq__(self, rhs):
        op = OP.IS if rhs is None else OP.EQ
        return Expression(self, op, rhs)

    def __ne__(self, rhs):
        op = OP.IS_NOT if rhs is None else OP.NE
        return Expression(self, op, rhs)

    __lt__ = _e(OP.LT)
    __le__ = _e(OP.LTE)
    __gt__ = _e(OP.GT)
    __ge__ = _e(OP.GTE)
    __lshift__ = _e(OP.IN)
    __rshift__ = _e(OP.IS)
    __mod__ = _e(OP.LIKE)
    __pow__ = _e(OP.ILIKE)

    bin_and = _e(OP.BIN_AND)
    bin_or = _e(OP.BIN_OR)
    in_ = _e(OP.IN)
    not_in = _e(OP.NOT_IN)
    regexp = _e(OP.REGEXP)

    # Special expressions.
    def is_null(self, is_null=True):
        op = OP.IS if is_null else OP.IS_NOT
        return Expression(self, op, None)

    def contains(self, rhs):
        return Expression(self, OP.ILIKE, '%%%s%%' % rhs)

    def startswith(self, rhs):
        return Expression(self, OP.ILIKE, '%s%%' % rhs)

    def endswith(self, rhs):
        return Expression(self, OP.ILIKE, '%%%s' % rhs)

    def between(self, lo, hi):
        return Expression(self, OP.BETWEEN, NodeList((lo, SQL('AND'), hi)))

    def concat(self, rhs):
        return StringExpression(self, OP.CONCAT, rhs)

    def __getitem__(self, item):
        if isinstance(item, slice):
            if item.start is None or item.stop is None:
                raise ValueError('BETWEEN range must have both a start- and '
                                 'end-point.')
            return self.between(item.start, item.stop)
        return self == item

    def distinct(self):
        return NodeList((SQL('DISTINCT'), self))

    def get_sort_key(self, ctx):
        return ()


class Expression(ColumnBase):
    def __init__(self, lhs, op, rhs, flat=False):
        self.lhs = lhs
        self.op = op
        self.rhs = rhs
        self.flat = flat

    def __sql__(self, ctx):
        overrides = {'parentheses': not self.flat}
        if isinstance(self.lhs, Field):
            overrides['converter'] = self.lhs.db_value
        else:
            overrides['converter'] = None

        if ctx.state.operations:
            op_sql = ctx.state.operations.get(self.op, self.op)
        else:
            op_sql = self.op

        with ctx(**overrides):
            # Postgresql reports an error for IN/NOT IN (), so convert to
            # the equivalent boolean expression.
            if self.op == OP.IN and Context().parse(self.rhs)[0] == '()':
                return ctx.literal('0 = 1')
            elif self.op == OP.NOT_IN and Context().parse(self.rhs)[0] == '()':
                return ctx.literal('1 = 1')

            return (ctx
                    .sql(self.lhs)
                    .literal(' %s ' % op_sql)
                    .sql(self.rhs))


class StringExpression(Expression):
    def __add__(self, rhs):
        return self.concat(rhs)

    def __radd__(self, lhs):
        return StringExpression(lhs, OP.CONCAT, self)


class SQL(ColumnBase):
    def __init__(self, sql, params=None):
        self.sql = sql
        self.params = params

    def __sql__(self, ctx):
        ctx.literal(self.sql)
        if self.params:
            for param in self.params:
                if isinstance(param, Node):
                    ctx.sql(param)
                else:
                    ctx.value(param)
        return ctx


def Check(constraint):
    return SQL('CHECK (%s)' % constraint)


class NodeList(ColumnBase):
    def __init__(self, nodes, glue=' ', parens=False):
        self.nodes = nodes
        self.glue = glue
        self.parens = parens
        if parens and len(self.nodes) == 1:
            if isinstance(self.nodes[0], Expression):
                # Hack to avoid double-parentheses.
                self.nodes[0].flat = True

    def __sql__(self, ctx):
        n_nodes = len(self.nodes)
        if n_nodes == 0:
            return ctx.literal('()') if self.parens else ctx
        with ctx(parentheses=self.parens):
            for i in range(n_nodes - 1):
                ctx.sql(self.nodes[i])
                ctx.literal(self.glue)
            ctx.sql(self.nodes[n_nodes - 1])
        return ctx


def CommaNodeList(nodes):
    return NodeList(nodes, ', ')


def EnclosedNodeList(nodes):
    return NodeList(nodes, ', ', True)


#: Represent a row tuple.
Tuple = lambda *a: EnclosedNodeList(a)


class WrappedNode(ColumnBase):
    def __init__(self, node):
        self.node = node

    def unwrap(self):
        return self.node.unwrap()


class BitwiseMixin(object):
    def __and__(self, other):
        return self.bin_and(other)

    def __or__(self, other):
        return self.bin_or(other)

    def __sub__(self, other):
        return self.bin_and(other.bin_negated())

    def __invert__(self):
        return BitwiseNegated(self)


class BitwiseNegated(BitwiseMixin, WrappedNode):
    def __invert__(self):
        return self.node

    def __sql__(self, ctx):
        if ctx.state.operations:
            op_sql = ctx.state.operations.get(self.op, self.op)
        else:
            op_sql = self.op
        return ctx.literal(op_sql).sql(self.node)


def Case(predicate, expression_tuples, default=None):
    clauses = [SQL('CASE')]
    if predicate is not None:
        clauses.append(predicate)
    for expr, value in expression_tuples:
        clauses.extend((SQL('WHEN'), expr, SQL('THEN'), value))
    if default is not None:
        clauses.extend((SQL('ELSE'), default))
    clauses.append(SQL('END'))
    return NodeList(clauses)


class Cast(WrappedNode):
    def __init__(self, node, cast):
        super(Cast, self).__init__(node)
        self.cast = cast

    def __sql__(self, ctx):
        return (
            ctx
            .literal('CAST(')
            .sql(self.node)
            .literal(' AS %s)' % self.cast)
        )


class Negated(WrappedNode):
    def __invert__(self):
        return self.node

    def __sql__(self, ctx):
        return ctx.literal('NOT ').sql(self.node)


class Ordering(WrappedNode):
    def __init__(self, node, direction, collation=None, nulls=None):
        super(Ordering, self).__init__(node)
        self.direction = direction
        self.collation = collation
        self.nulls = nulls

    def collate(self, collation=None):
        return Ordering(self.node, self.direction, collation)

    def __sql__(self, ctx):
        ctx.sql(self.node).literal(' %s' % self.direction)
        if self.collation:
            ctx.literal(' COLLATE %s' % self.collation)
        if self.nulls:
            ctx.literal(' NULLS %s' % self.nulls)
        return ctx


def Asc(node, collation=None, nulls=None):
    return Ordering(node, 'ASC', collation, nulls)


def Desc(node, collation=None, nulls=None):
    return Ordering(node, 'DESC', collation, nulls)


class Entity(ColumnBase):
    def __init__(self, *path):
        self._path = [part.replace('"', '""') for part in path if part]

    def __getattr__(self, attr):
        return Entity(*self._path + [attr])

    def get_sort_key(self, ctx):
        return tuple(self._path)

    def __hash__(self):
        return hash((self.__class__.__name__, tuple(self._path)))

    def __sql__(self, ctx):
        return ctx.literal(quote(self._path, ctx.state.quote or '"'))


class EntityFactory:
    __slots__ = ('node',)

    def __init__(self, node):
        self.node = node

    def __getattr__(self, attr):
        return Entity(self.node, attr)


class _DynamicEntity(object):
    __slots__ = ()

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return EntityFactory(instance._alias)  # Implements __getattr__().
        return self


class Alias(WrappedNode):
    c = _DynamicEntity()

    def __init__(self, node, alias):
        super(Alias, self).__init__(node)
        self._alias = alias

    def alias(self, alias=None):
        if alias is None:
            return self.node
        else:
            return Alias(self.node, alias)

    def unalias(self):
        return self.node

    def __sql__(self, ctx):
        if ctx.scope == SCOPE_SOURCE:
            return (ctx
                    .sql(self.node)
                    .literal(' AS ')
                    .sql(Entity(self._alias)))
        else:
            return ctx.sql(Entity(self._alias))


class QualifiedNames(WrappedNode):
    def __sql__(self, ctx):
        with ctx.scope_column():
            return ctx.sql(self.node)


__all__ = ['ColumnBase', 'Expression', 'StringExpression',
           'SQL', 'Check', 'NodeList', 'CommaNodeList',
           'EnclosedNodeList', 'Tuple', 'WrappedNode',
           'BitwiseMixin', 'BitwiseNegated', 'Negated',
           'Ordering', 'Asc', 'Desc',
           'Entity', 'EntityFactory','QualifiedNames']
