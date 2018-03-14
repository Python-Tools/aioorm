from aioorm.query.update import Update
from .model_query_helper import _ModelWriteQueryHelper


class ModelUpdate(_ModelWriteQueryHelper, Update):
    pass
