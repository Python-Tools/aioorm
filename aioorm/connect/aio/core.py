import abc
import asyncio
import aiomysql
from typing import (
    Any,
    Dict,
    AsyncGenerator
)
from aioorm.abcs.connect import ConnectBase
from ..error import NotConnectYet


class AioConnectBase(ConnectBase):

    @property
    def pool(self):
        """连接对象的连接池

        Raises:
            NotConnectYet: 未了连接时抛出

        Returns:
            [aiomysql.pool.Pool]: 连接好时返回
        """

        if self._pool is None:
            raise NotConnectYet("please connect again")
        return self._pool

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @abc.abstractmethod
    async def connect(self):
        pass

    async def close(self):
        """关闭连接

        Returns:
            (Any): 返回关闭状态
        """

        self.pool.close()
        rst = await self.pool.wait_closed()
        self._pool = None
        return rst

    async def execute_sql(self, sql_str: str, row_type=None)->AsyncGenerator[Any, Any]:
        """执行sql字符串.

        异步生成器函数

        Args:
            sql_str (str): [description]
            row_type (Any, optional): Defaults to None. 
        """

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

    async def execute(self, sql_query)->AsyncGenerator[Any, Any]:
        """执行query对象.

        Args:
            sql_query ('aioorm.query.Query'): 要执行的query对象
        """

        sql_str = sql_query.sql
        row_type = sql_query.row_type
        async for row in execute_sql(sql_str, row_type):
            yield row
