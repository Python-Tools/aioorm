import operator
from functools import reduce
from aioorm.ast.entity import CommaNodeList
from .meta_fields import MetaField


class CompositeKey(MetaField):
    sequence = None

    def __init__(self, *field_names):
        self.field_names = field_names

    def __get__(self, instance, instance_type=None):
        if instance is not None:
            return tuple([getattr(instance, field_name)
                          for field_name in self.field_names])
        return self

    def __set__(self, instance, value):
        if not isinstance(value, (list, tuple)):
            raise TypeError('A list or tuple must be used to set the value of '
                            'a composite primary key.')
        if len(value) != len(self.field_names):
            raise ValueError('The length of the value must equal the number '
                             'of columns of the composite primary key.')
        for idx, field_value in enumerate(value):
            setattr(instance, self.field_names[idx], field_value)

    def __eq__(self, other):
        expressions = [(self.model._meta.fields[field] == value)
                       for field, value in zip(self.field_names, other)]
        return reduce(operator.and_, expressions)

    def __ne__(self, other):
        return ~(self == other)

    def __hash__(self):
        return hash((self.model.__name__, self.field_names))

    def __sql__(self, ctx):
        return ctx.sql(CommaNodeList([self.model._meta.fields[field]
                                      for field in self.field_names]))

    def bind(self, model, name, set_attribute=True):
        self.model = model
        self.column_name = self.name = name
        setattr(model, self.name, self)
