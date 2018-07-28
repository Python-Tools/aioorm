class Query:

    def __repr__(self):
        return self._cache_sql

    def __init__(self,*args,**kwargs):
        self._cache_sql = ""
        self._row_type = None

    @property
    def sql_str(self):
        return self._cache_sql+";"

    @property
    def row_type(self):
        return self._row_type

    


