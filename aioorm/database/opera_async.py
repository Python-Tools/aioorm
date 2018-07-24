from aioorm.query.ddl import (
    CreateQuery,
    DropQuery
)

async def drop_dbAsync(self,dbname=None):
    if dbname is None:
        dbname = self.dbname
    query = DropQuery().database(dbname)
    result = []
    async for row in self.execute(query):
        result.append(row)
    return result