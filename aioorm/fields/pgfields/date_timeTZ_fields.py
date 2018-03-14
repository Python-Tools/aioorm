from ..datetime_fields import DateTimeField


class DateTimeTZField(DateTimeField):
    field_type = 'TIMESTAMPTZ'
