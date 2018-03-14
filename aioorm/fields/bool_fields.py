from .field import Field


class BooleanField(Field):
    field_type = 'BOOL'
    coerce = bool
