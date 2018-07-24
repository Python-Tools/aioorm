"""Data Definition Language数据定义语言.


用来创建或者删除存储 数据用的数据库以及数据库中的表等对象,通常包括:

CREATE:创建数据库和表等对象 
DROP: 删除数据库和表等对象 
ALTER: 修改数据库和表等对象的结构

考虑到orm的特殊性,这边只实现CREATE和DROP
"""

from .create_query import CreateQuery
from .drop_query import DropQuery

__all__=['CreateQuery','DropQuery']