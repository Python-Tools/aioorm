import collections


class attrdict(dict):
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        self[attr] = value

    def __iadd__(self, rhs):
        self.update(rhs)
        return self

    def __add__(self, rhs):
        d = attrdict(self)
        d.update(rhs)
        return d


SENTINEL = object()
#: Operations for use in SQL expressions.
OP = attrdict(
    AND='AND',
    OR='OR',
    ADD='+',
    SUB='-',
    MUL='*',
    DIV='/',
    BIN_AND='&',
    BIN_OR='|',
    XOR='#',
    MOD='%',
    EQ='=',
    LT='<',
    LTE='<=',
    GT='>',
    GTE='>=',
    NE='!=',
    IN='IN',
    NOT_IN='NOT IN',
    IS='IS',
    IS_NOT='IS NOT',
    LIKE='LIKE',
    ILIKE='ILIKE',
    BETWEEN='BETWEEN',
    REGEXP='REGEXP',
    CONCAT='||',
    BITWISE_NEGATION='~'
)
# To support "django-style" double-underscore filters, create a mapping between
# operation name and operation code, e.g. "__eq" == OP.EQ.

DJANGO_MAP = attrdict(
    {
        'eq': OP.EQ,
        'lt': OP.LT,
        'lte': OP.LTE,
        'gt': OP.GT,
        'gte': OP.GTE,
        'ne': OP.NE,
        'in': OP.IN,
        'is': OP.IS,
        'like': OP.LIKE,
        'ilike': OP.ILIKE,
        'regexp': OP.REGEXP
    }
)

#: Mapping of field type to the data-type supported by the database. Databases
#: may override or add to this list.
FIELD = attrdict(
    AUTO='INTEGER',
    BIGAUTO='BIGINT',
    BIGINT='BIGINT',
    BLOB='BLOB',
    BOOL='SMALLINT',
    CHAR='CHAR',
    DATE='DATE',
    DATETIME='DATETIME',
    DECIMAL='DECIMAL',
    DEFAULT='',
    DOUBLE='REAL',
    FLOAT='REAL',
    INT='INTEGER',
    SMALLINT='SMALLINT',
    TEXT='TEXT',
    TIME='TIME',
    UUID='TEXT',
    VARCHAR='VARCHAR'
)

#: Join helpers (for convenience) -- all join types are supported, this object
#: is just to help avoid introducing errors by using strings everywhere.
JOIN = attrdict(
    INNER='INNER',
    LEFT_OUTER='LEFT OUTER',
    RIGHT_OUTER='RIGHT OUTER',
    FULL='FULL',
    FULL_OUTER='FULL OUTER',
    CROSS='CROSS'
)

# Row representations.
ROW = attrdict(
    TUPLE=1,
    DICT=2,
    NAMED_TUPLE=3,
    CONSTRUCTOR=4,
    MODEL=5
)
# Helper functions that are used in various parts of the codebase.
MODEL_BASE = '_metaclass_helper_'

# 规定界限范围
SCOPE_NORMAL = 1
SCOPE_SOURCE = 2
SCOPE_VALUES = 4
SCOPE_CTE = 8
SCOPE_COLUMN = 16

IndexMetadata = collections.namedtuple(
    'IndexMetadata',
    ('name', 'sql', 'columns', 'unique', 'table')
)
ColumnMetadata = collections.namedtuple(
    'ColumnMetadata',
    ('name', 'data_type', 'null', 'primary_key', 'table')
)
ForeignKeyMetadata = collections.namedtuple(
    'ForeignKeyMetadata',
    ('column', 'dest_table', 'dest_column', 'table')
)

# pg
HCONTAINS_DICT = '@>'
HCONTAINS_KEYS = '?&'
HCONTAINS_KEY = '?'
HCONTAINS_ANY_KEY = '?|'
HKEY = '->'
HUPDATE = '||'
ACONTAINS = '@>'
ACONTAINS_ANY = '&&'
TS_MATCH = '@@'
JSONB_CONTAINS = '@>'
JSONB_CONTAINED_BY = '<@'
JSONB_CONTAINS_ANY_KEY = '?|'
JSONB_CONTAINS_ALL_KEYS = '?&'
JSONB_EXISTS = '?'
