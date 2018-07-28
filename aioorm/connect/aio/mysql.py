import asyncio
from typing import Optional
import aiomysql
from .core import AioConnectBase


class MysqlConnect(AioConnectBase):
    """Mysql的连接对象.

    Attributes:
        username (str): 登录用户名
        password (str): 登录密码
        host (str): 登录目标主机名或ip
        port (int): 登录目标主机端口
        database (str): 登录的数据库
        loop (asyncio.AbstractEventLoop): 事件循环
        kwargs (Dict[str,Any]): 建立连接池时候的关键字参数

        pool (aiomysql.pool.Pool): aiomysql的连接池对象(property)
    """

    def __init__(self, *, username: str="root",
                 password: str="",
                 host: str="localhost",
                 port: int=3306,
                 database: str='mysql',
                 loop: Optional[asyncio.AbstractEventLoop] =None,
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
            (aiomysql.pool.Pool): 返回池对象
        """

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
