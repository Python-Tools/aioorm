from aioorm.model.model import Model
from aioorm.model.model_select import ModelSelect
from aioorm.ast.entity import SQL
from aioorm.reflect import ensure_tuple
from .select import SelectQuery


class ManyToManyQuery(ModelSelect):
    def __init__(self, instance, accessor, rel, *args, **kwargs):
        self._instance = instance
        self._accessor = accessor
        super(ManyToManyQuery, self).__init__(rel, (rel,), *args, **kwargs)

    def _id_list(self, model_or_id_list):
        if isinstance(model_or_id_list[0], Model):
            return [obj._pk for obj in model_or_id_list]
        return model_or_id_list

    def add(self, value, clear_existing=False):
        if clear_existing:
            self.clear()

        accessor = self._accessor
        if isinstance(value, SelectQuery):
            query = value.columns(
                SQL(str(self._instance._pk)),
                accessor.rel_model._meta.primary_key)
            accessor.through_model.insert_from(
                fields=[accessor.src_fk, accessor.dest_fk],
                query=query).execute()
        else:
            value = ensure_tuple(value)
            if not value:
                return
            inserts = [{
                accessor.src_fk.name: self._instance._pk,
                accessor.dest_fk.name: rel_id}
                for rel_id in self._id_list(value)]
            accessor.through_model.insert_many(inserts).execute()

    def remove(self, value):
        if isinstance(value, SelectQuery):
            subquery = value.columns(value.model._meta.primary_key)
            return (self._accessor.through_model
                    .delete()
                    .where(
                        (self._accessor.dest_fk << subquery) &
                        (self._accessor.src_fk == self._instance._pk))
                    .execute())
        else:
            value = ensure_tuple(value)
            if not value:
                return
            return (self._accessor.through_model
                    .delete()
                    .where(
                        (self._accessor.dest_fk << self._id_list(value)) &
                        (self._accessor.src_fk == self._instance._pk))
                    .execute())

    def clear(self):
        return (self._accessor.through_model
                .delete()
                .where(self._accessor.src_fk == self._instance)
                .execute())
