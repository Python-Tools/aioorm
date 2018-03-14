from aioorm.const import ROW
from aioorm.query.insert import Insert
from .model_query_helper import _ModelWriteQueryHelper


class ModelInsert(_ModelWriteQueryHelper, Insert):
    def __init__(self, *args, **kwargs):
        super(ModelInsert, self).__init__(*args, **kwargs)
        if self._returning is None and self.model._meta.database is not None:
            if self.model._meta.database.returning_clause:
                self._returning = self.model._meta.get_primary_keys()
                self._row_type = ROW.TUPLE

    def get_default_data(self):
        return self.model._meta.defaults
