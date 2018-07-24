from aioorm.entity.table import Table
from aioorm.entity.view import View
from typing import Any
from ..core import Query

class CreateQuery(Query):

    def __init__(self):
        super().__init__()
        self._cache_sql="CREATE "

    def table(self,entity:Any)->CreateQuery:
        """创建表
        
        Args:
            entity (Any): 参数为一个类对象,且必须是Table的子类
        
        Raises:
            SqlEnd:如果sql已经结束则抛出
            ParamError: 参数不是Table的子类时抛出该异常
        
        Returns:
            CreateQuery: 返回自身
        """
        if self.end = True:
            raise SqlEnd("create query already end: {self._cache_sql}")
        if not issubclass(entity,Table):
            raise ParamError("entity must be subclass of Table")
        # TODO
        # self._cache_sql="""TABLE {entity.__name__} 
        # (

        # )
        # """
        self.end = True
        return self

    def database(self,entity:str)->CreateQuery:
        """创建数据库
        
        Args:
            entity (str): 要创建的database名
        
        Raises:
            SqlEnd: 如果sql已经结束则抛出
        
        Returns:
            CreateQuery: 语句自身
        """
        if self.end = True:
            raise SqlEnd("create query already end: {self._cache_sql}")
     
        self._cache_sql += f"Database {entity}"
        self.end = True
        return self

    def view(self,entity:Any)->CreateQuery:
        if self.end = True:
            raise SqlEnd("create query already end: {self._cache_sql}")
        if not issubclass(entity,View):
            raise ParamError("entity must be subclass of View")
        # TODO
        # self._cache_sql="""VIEW ({})
        # AS 
        # entity.select_sql

        # ;
        # """
        self.end = True
        return self
        