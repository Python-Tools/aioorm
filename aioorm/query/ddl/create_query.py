from aioorm.abcs.entity import TableBase
from aioorm.entity.view import View
from typing import Any
from aioorm.abcs.query import Query


class CreateQuery(Query):

    def __init__(self):
        super().__init__()
        self._cache_sql = "CREATE "

    def database(self, entity: str)->CreateQuery:
        """创建数据库

        Args:
            entity (str): 要创建的database名

        Raises:
            SqlEnd: 如果sql已经结束则抛出

        Returns:
            CreateQuery: 语句自身
        """

        self._cache_sql += f"Database {entity}"
        return self

    def table(self, entity: Any)->CreateQuery:
        """创建表

        Args:
            entity (Any): 参数为一个类对象,且必须是Table的子类

        Raises:
            SqlEnd:如果sql已经结束则抛出
            ParamError: 参数不是Table的子类时抛出该异常

        Returns:
            CreateQuery: 返回自身
        """

        if not issubclass(entity, TableBase):
            raise ParamError("entity must be subclass of Table")
        # TODO
        # self._cache_sql="""TABLE {entity.__name__}
        # (

        # )
        # """
        return self

    def view(self, entity: Any)->CreateQuery:
        if not issubclass(entity, ViewBase):
            raise ParamError("entity must be subclass of View")
        # TODO
        # self._cache_sql="""VIEW ({})
        # AS
        # entity.select_sql

        # ;
        # """
        return self

    def index(self, *entity, name=None, unique=False)->CreateQuery:
        pass
