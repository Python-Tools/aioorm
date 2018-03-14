import collections


class PrefetchQuery(collections.namedtuple('_PrefetchQuery', (
        'query', 'fields', 'is_backref', 'rel_models', 'field_to_name', 'model'))):
    def __new__(cls, query, fields=None, is_backref=None, rel_models=None,
                field_to_name=None, model=None):
        if fields:
            if is_backref:
                rel_models = [field.model for field in fields]
                foreign_key_attrs = [field.rel_field.name for field in fields]
            else:
                rel_models = [field.rel_model for field in fields]
                foreign_key_attrs = [field.name for field in fields]
            field_to_name = list(zip(fields, foreign_key_attrs))
        model = query.model
        return super(PrefetchQuery, cls).__new__(
            cls, query, fields, is_backref, rel_models, field_to_name, model)

    def populate_instance(self, instance, id_map):
        if self.is_backref:
            for field in self.fields:
                identifier = instance.__data__[field.name]
                key = (field, identifier)
                if key in id_map:
                    setattr(instance, field.name, id_map[key])
        else:
            for field, attname in self.field_to_name:
                identifier = instance.__data__[field.rel_field.name]
                key = (field, identifier)
                rel_instances = id_map.get(key, [])
                for inst in rel_instances:
                    setattr(inst, attname, instance)
                setattr(instance, field.backref, rel_instances)

    def store_instance(self, instance, id_map):
        for field, attname in self.field_to_name:
            identity = field.rel_field.python_value(instance.__data__[attname])
            key = (field, identity)
            if self.is_backref:
                id_map[key] = instance
            else:
                id_map.setdefault(key, [])
                id_map[key].append(instance)
