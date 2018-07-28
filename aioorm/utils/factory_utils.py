from ..postgresql import AioPostgreSQLDatabase
from ..mysql import AioMySQLDatabase
from ..uri_parser import parser

from typing import TypeVar
AnyDb = TypeVar('AnyDb', AioMySQLDatabase, AioPostgreSQLDatabase)

DBS = {
    'mysql':AioMySQLDatabase,
    'postgresql':AioPostgreSQLDatabase
}



def AioDbFactory(uri:str)->AnyDb:
    info = parser(uri)
    db = DBS.get(info.get("scheme"))(
        info.get('database'),
        host=info.get("host"),
        port=info.get("port"),
        user=info.get("username"),
        password=info.get("password"))
    print(db)
    return db
