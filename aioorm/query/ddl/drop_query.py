from aioorm.entity.table import Table
from aioorm.entity.view import View
from typing import Any
from aioorm.abcs.query import Query

class DropQuery(Query):
    def __init__(self):
        super().__init__()
        self._cache_sql="DROP "

    def table(self,entity:Any,safe=False)->CreateQuery:
        """删除表
        
        Args:
            entity (Any): 参数为一个类对象,且必须是Table的子类
        
        Raises:
            SqlEnd:如果sql已经结束则抛出
            ParamError: 参数不是Table的子类时抛出该异常
        
        Returns:
            CreateQuery: 返回自身
        """

        if not issubclass(entity,Table):
            raise ParamError("entity must be subclass of Table")
        if safe:
            self._cache_sql=f"TABLE IF EXISTS {entity.__name__}"
        else:
            self._cache_sql=f"TABLE {entity.__name__}"
        return self

    def database(self,entity:str)->CreateQuery:
        """删除数据库
        
        Args:
            entity (str): 要创建的database名
        
        Raises:
            SqlEnd: 如果sql已经结束则抛出
        
        Returns:
            CreateQuery: 语句自身
        """
     
        self._cache_sql += f"Database {entity.__name__}"
        return self

    def view(self,entity:Any)->CreateQuery:
        if not issubclass(entity,View):
            raise ParamError("entity must be subclass of View")
        self._cache_sql=f"""VIEW {entity.__name__}"""

        return self