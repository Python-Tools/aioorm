import asyncio
from typing import Optional
import aiopg
from .core import AioConnectBase


class PostgresqlConnect(AioConnectBase):

    def __init__(self, *, username: str="postgres",
                 password: str="",
                 host: str="localhost",
                 port: int=5432,
                 database: str='postgres',
                 loop: Optional[asyncio.AbstractEventLoop]=None,
                 **kwargs):

        super().__init__(
            username=username,
            password=password,
            host=host,
            port=port,
            database=database,
            loop=loop,
            **kwargs
        )

    async def connect(self):
        """建立连接.

        Returns:
            (aiopg.pool.Pool): 返回池对象
        """

        if self.password:
            dsn = f"dbname={self.database} user={self.username} password={self.password} host={self.host} port={self.port}"
        else:
            dsn = f"dbname={self.database} user={self.username} host={self.host} port={self.port}"
        self._pool = await aiopg.create_pool(
            dsn=dsn,
            loop=self.loop,
            **self.kwargs
        )
        return self._pool
