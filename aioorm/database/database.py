import asyncio
from types import MethodType




class Database:

    def __init__(self,connection):
        self.connection = connection
        self.dbname = connection.database
        self.tables = set()
        self.views = set()
        self.execute_sql=connection.execute_sql
        self.execute=connection.execute
        if asyncio.iscoroutinefunction(self.execute):
            
            self.create_db = MethodType(create_dbAsync, self)
            self.drop_db = MethodType(create_dbAsync, self)
            self.create_tables = MethodType(create_dbAsync, self)
            self.drop_tables = MethodType(create_dbAsync, self)
            self.create_views = MethodType(create_dbAsync, self)
            self.drop_views = MethodType(create_dbAsync, self)
        else:
            self.create_db = MethodType(create_dbAsync, self)
            self.drop_db = MethodType(create_dbAsync, self)
            self.create_tables = MethodType(create_dbAsync, self)
            self.drop_tables = MethodType(create_dbAsync, self)
            self.create_views = MethodType(create_dbAsync, self)
            self.drop_views = MethodType(create_dbAsync, self)

