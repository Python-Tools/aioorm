import abc


class ConstrainBase(abc.ABC):
    """制约条件.

    包括:
    + Primary
    + Set
    + Require
    + Option
    + Index
    + Unique
    + Check
    """

    __counter = 0

    def __init__(self):
        cls = self.__class__
        prefix = cls.__name__
        index = cls.__counter
        self.storage_name = '_{}#{}'.format(prefix, index)
        cls.__counter += 1

    def __get__(self, instance, owner):
        if instance is None:
            return self
        else:
            return getattr(instance, self.storage_name)

    def __set__(self, instance, value):
        setattr(instance, self.storage_name, value)

    def __set_name__(self, owner, name):
        self.name = name
