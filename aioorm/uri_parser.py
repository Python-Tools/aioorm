__all__ = ['parser']
import platform
import getpass
from collections import namedtuple
from urllib.parse import urlparse,ParseResult,parse_qsl

from .error import *

from typing import Dict,Optional,Tuple,Union,Any




Default = namedtuple('Default',['user','password','host','port'])

if platform.system() == 'Darwin':
    user = getpass.getuser()
    password = ''
elif platform.system() == 'windows':
    user = 'postgres'
    password = 'postgres'
else:
    user = 'postgres'
    password = ''

DEFAULT_INFO = {
    'mysql':Default(user='root',password='',host='localhost',port='3306'),
    'postgresql':Default(user=user,password=password,host='localhost',port='5432')
}

def check_scheme(scheme:Optional[str])->str:

    SCHEMES = ('mysql','postgresql')
    if scheme:
        if scheme.lower() in SCHEMES:
            return scheme.lower()
        else:
            raise InvalidURI("unknow database")
    else:
        raise InvalidURI("must have a database uri")

def check_netloc(parse_result:ParseResult,scheme:str)->Tuple[Optional[str],Optional[str],Optional[str],Optional[str]]:
    default = DEFAULT_INFO.get(scheme)

    user = parse_result.username or default.user
    password = parse_result.password or default.password
    host = parse_result.hostname or default.host
    if parse_result.port:
        port = str(parse_result.port)
    else:
        port = default.port
    return user,password,host,port

def check_path(path:str)->str:
    if path:
        return path.replace("/","")
    else:
        raise InvalidURI("need to point out the db's name")

def check_query(query:str)->Any:
    if query:
        return dict(parse_qsl(query))
    else:
        return None


def parser(uri:str)->Dict[str,str]:
    parse_result = urlparse(uri)
    scheme = check_scheme(parse_result.scheme)
    usr,password,host,port = check_netloc(parse_result,scheme)
    db = check_path(parse_result.path)
    query = check_query(parse_result.query)

    result = dict(
    scheme=scheme,
    username = usr,
    password = password,
    host = host,
    port = int(port),
    database = db
    )
    if query:
        result.update(**query)
    return result
