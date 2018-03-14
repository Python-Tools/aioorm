from .field import Field


class _StringField(Field):
    def coerce(self, value):
        if isinstance(value, str):
            return value
        elif isinstance(value, str):
            return value.decode('utf-8')
        return str(value)

    def __add__(self, other):
        return self.concat(other)

    def __radd__(self, other):
        return other.concat(self)


class CharField(_StringField):
    field_type = 'VARCHAR'

    def __init__(self, max_length=255, *args, **kwargs):
        self.max_length = max_length
        super().__init__(*args, **kwargs)

    def get_modifiers(self):
        return self.max_length and [self.max_length] or None


class FixedCharField(CharField):
    field_type = 'CHAR'

    def python_value(self, value):
        value = super().python_value(value)
        if value:
            value = value.strip()
        return value


class TextField(_StringField):
    field_type = 'TEXT'
