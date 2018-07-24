class Query:

    def __repr__(self):
        return self._cache_sql

    def __init__(self,*args,**kwargs):
        self._cache_sql = ""
        self._return_row = None
        self.end = False

    @property
    def sql(self):
        return self._cache_sql

    @property
    def return_row(self):
        return self._return_row

    


