from aioorm.utils import __deprecated__
from .field import Field


class IntegerField(Field):
    field_type = 'INT'
    coerce = int


class BigIntegerField(IntegerField):
    field_type = 'BIGINT'


class SmallIntegerField(IntegerField):
    field_type = 'SMALLINT'


class AutoField(IntegerField):
    auto_increment = True
    field_type = 'AUTO'

    def __init__(self, *args, **kwargs):
        if kwargs.get('primary_key') is False:
            raise ValueError('{} must always be a primary key.'.format(type(self)))
        kwargs['primary_key'] = True
        super(AutoField, self).__init__(*args, **kwargs)


class BigAutoField(AutoField):
    field_type = 'BIGAUTO'


class PrimaryKeyField(AutoField):
    def __init__(self, *args, **kwargs):
        __deprecated__('"PrimaryKeyField" has been renamed to "AutoField". '
                       'Please update your code accordingly as this will be '
                       'completely removed in a subsequent release.')
        super(PrimaryKeyField, self).__init__(*args, **kwargs)
