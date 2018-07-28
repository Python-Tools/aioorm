
class ColumnBase:
    """列定义.
    
    对应的类型:

    python|mysql|pg
    ---|---|---
    int|INTEGER|INTEGER
    float|
    
    + str:
    + datetime.datetime|datetime|timestamp
    + datetime.date|date|date
    + time
    + dict
    + 

    """

    def __init__(self, attrtype, not_null=True, default=None, unique=False):
        self.attrtype = attrtype
        self.not_null = not_null
        self.default = default
        self.unique = unique
        self.name = None

    def _create_sql(self):
        if self.name is None:
            assert False, "need name"
        if isinstance(attrtype,str)
        sql_str = f"'{self.name}' {}"