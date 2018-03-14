from aioorm.query.base import RawQuery
from .model_query_helper import _ModelQueryHelper


class ModelRaw(_ModelQueryHelper, RawQuery):
    def __init__(self, model, sql, params, **kwargs):
        self.model = model
        self._returning = ()
        super(ModelRaw, self).__init__(sql=sql, params=params, **kwargs)

    def get(self):
        try:
            return self.execute()[0]
        except IndexError:
            sql, params = self.sql()
            raise self.model.DoesNotExist(
                '{} instance matching query does not exist:\nSQL: {}\nParams: {}'.format(
                    self.model, sql, params
                )
            )
