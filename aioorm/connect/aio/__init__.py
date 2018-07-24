from .mysql import MysqlConnect
from .postgresql import PostgresqlConnect
from ..utils.url_parser import parser
from typing import TypeVar

AnyDb = TypeVar('AnyDb', MysqlConnect, PostgresqlConnect)

DBS = {
    'mysql': MysqlConnect,
    'postgresql': PostgresqlConnect
}


def dbconnect(uri: str, loop=None)->AnyDb:
    info = parser(uri)
    db = DBS.get(info.get("scheme"))
    del info["scheme"]
    connect = db(loop=loop, **info)
    return connect
