from aioorm.query.delete import Delete
from .model_query_helper import _ModelWriteQueryHelper


class ModelDelete(_ModelWriteQueryHelper, Delete):
    pass
