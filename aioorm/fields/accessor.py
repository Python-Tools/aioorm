class FieldAccessor:
    def __init__(self, model, field, name):
        self.model = model
        self.field = field
        self.name = name

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return instance.__data__.get(self.name)
        return self.field

    def __set__(self, instance, value):
        instance.__data__[self.name] = value
        instance._dirty.add(self.name)


class ForeignKeyAccessor:
    def __init__(self, model, field, name):
        super(ForeignKeyAccessor, self).__init__(model, field, name)
        self.rel_model = field.rel_model

    def get_rel_instance(self, instance):
        value = instance.__data__.get(self.name)
        if value is not None or self.name in instance.__rel__:
            if self.name not in instance.__rel__:
                obj = self.rel_model.get(self.field.rel_field == value)
                instance.__rel__[self.name] = obj
            return instance.__rel__[self.name]
        elif not self.field.null:
            raise self.rel_model.DoesNotExist
        return value

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return self.get_rel_instance(instance)
        return self.field

    def __set__(self, instance, obj):
        if isinstance(obj, self.rel_model):
            instance.__data__[self.name] = getattr(obj, self.field.rel_field.name)
            instance.__rel__[self.name] = obj
        else:
            fk_value = instance.__data__.get(self.name)
            instance.__data__[self.name] = obj
            if obj != fk_value and self.name in instance.__rel__:
                del instance.__rel__[self.name]
        instance._dirty.add(self.name)


class BackrefAccessor:
    def __init__(self, field):
        self.field = field
        self.model = field.rel_model
        self.rel_model = field.model

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            dest = self.field.rel_field.name
            return (self.rel_model
                    .select()
                    .where(self.field == getattr(instance, dest)))
        return self


class ObjectIdAccessor:
    """Gives direct access to the underlying id"""

    def __init__(self, field):
        self.field = field

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return instance.__data__.get(self.field.name)
        return self.field

    def __set__(self, instance, value):
        setattr(instance, self.field.name, value)
