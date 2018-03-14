from aioorm.database.proxy import Proxy
from .field import Field


class BlobField(Field):
    field_type = 'BLOB'

    def bind(self, model, name, set_attribute=True):
        self._constructor = bytearray
        if model._meta.database:
            if isinstance(model._meta.database, Proxy):
                def cb(db):
                    self._constructor = db.get_binary_type()
                model._meta.database.attach_callback(cb)
            else:
                self._constructor = model._meta.database.get_binary_type()
        return super(BlobField, self).bind(model, name, set_attribute)

    def db_value(self, value):
        if isinstance(value, str):
            value = value.encode('raw_unicode_escape')
        if isinstance(value, bytes):
            return self._constructor(value)
        return value
