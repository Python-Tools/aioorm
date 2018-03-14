import uuid
from .field import Field


class UUIDField(Field):
    field_type = 'UUID'

    def db_value(self, value):
        if isinstance(value, uuid.UUID):
            return value.hex
        try:
            return uuid.UUID(value).hex
        except:
            return value

    def python_value(self, value):
        if isinstance(value, uuid.UUID):
            return value
        return None if value is None else uuid.UUID(value)
