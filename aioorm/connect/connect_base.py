import abc
import asyncio
from typing import (
    Any
)
from .utils.url_parser import parser


class ConnectBase(abc.ABC):

    @classmethod
    def from_url(clz, url):
        kwargs = parser(url)
        return clz(kwargs)

    def __init__(self, *, username,
                 password,
                 host,
                 port,
                 database,
                 loop, **kwargs):

        self.username = username or ""
        self.password = password
        self.host = host
        self.port = port
        self.database = database
        self.loop = loop if loop else asyncio.get_event_loop()
        self.kwargs = dict(kwargs)
        self._pool = None

    @abc.abstractproperty
    def pool(self):
        pass

    @abc.abstractmethod
    def connect(self):
        pass

    @abc.abstractmethod
    def close(self):
        pass

    @abc.abstractmethod
    def execute_sql(self, sql_str: str):
        pass

    @abc.abstractmethod
    def execute(self, sql_ast):
        pass
