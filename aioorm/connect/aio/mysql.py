import aiomysql

from ..connect_base import ConnectBase
from ..error import NotConnectYet


class MysqlConnect(ConnectBase):

    def __init__(self, *, username="root",
                 password="",
                 host="localhost",
                 port=3306,
                 database='mysql',
                 loop=None, **kwargs):

        super().__init__(
            username=username,
            password=password,
            host=host,
            port=port,
            database=database,
            loop=loop,
            **kwargs
        )

    @property
    def pool(self):
        if self._pool is None:
            raise NotConnectYet("please connect again")
        return self._pool

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        self._pool = await aiomysql.create_pool(
            host=self.host,
            port=self.port,
            user=self.username,
            password=self.password,
            db=self.database,
            loop=self.loop,
            **self.kwargs
        )
        return self._pool

    async def close(self):
        self.pool.close()
        rst = await self.pool.wait_closed()
        self._pool = None
        return rst

    async def execute_sql(self, sql_str: str, row_type=None):
        if not sql_str.endswith(";"):
            sql_str = sql_str + ";"
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql_str)
                async for row in cur:
                    if row_type is None:
                        yield row
                    else:
                        row_type(*row)

    async def execute(self, sql_ast):
        sql_str = sql_ast.sql
        row_type = sql_ast.return_row
        async for row in execute_sql(sql_str, row_type):
            yield row
