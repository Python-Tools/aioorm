from aioorm.ast.entity import BitwiseMixin
from .integer_fields import BigIntegerField
from .accessor import FieldAccessor
from .blob_fields import BlobField


class BitField(BitwiseMixin, BigIntegerField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', 0)
        super().__init__(*args, **kwargs)

    def flag(self, value):
        class FlagDescriptor(object):
            def __init__(self, field, value):
                self._field = field
                self._value = value

            def __get__(self, instance, instance_type=None):
                if instance is None:
                    return self._field.bin_and(self._value) != 0
                value = getattr(instance, self._field.name) or 0
                return (value & self._value) != 0

            def __set__(self, instance, is_set):
                if is_set not in (True, False):
                    raise ValueError('Value must be either True or False')
                value = getattr(instance, self._field.name) or 0
                if is_set:
                    value |= self._value
                else:
                    value &= ~self._value
                setattr(instance, self._field.name, value)
        return FlagDescriptor(self, value)


class BigBitFieldData:
    def __init__(self, instance, name):
        self.instance = instance
        self.name = name
        value = self.instance.__data__.get(self.name)
        if not value:
            value = bytearray()
        elif not isinstance(value, bytearray):
            value = bytearray(value)
        self._buffer = self.instance.__data__[self.name] = value

    def _ensure_length(self, idx):
        byte_num, byte_offset = divmod(idx, 8)
        cur_size = len(self._buffer)
        if cur_size <= byte_num:
            self._buffer.extend(b'\x00' * ((byte_num + 1) - cur_size))
        return byte_num, byte_offset

    def set_bit(self, idx):
        byte_num, byte_offset = self._ensure_length(idx)
        self._buffer[byte_num] |= (1 << byte_offset)

    def clear_bit(self, idx):
        byte_num, byte_offset = self._ensure_length(idx)
        self._buffer[byte_num] &= ~(1 << byte_offset)

    def toggle_bit(self, idx):
        byte_num, byte_offset = self._ensure_length(idx)
        self._buffer[byte_num] ^= (1 << byte_offset)
        return bool(self._buffer[byte_num] & (1 << byte_offset))

    def is_set(self, idx):
        byte_num, byte_offset = self._ensure_length(idx)
        return bool(self._buffer[byte_num] & (1 << byte_offset))

    def __repr__(self):
        return repr(self._buffer)


class BigBitFieldAccessor(FieldAccessor):
    def __get__(self, instance, instance_type=None):
        if instance is None:
            return self.field
        return BigBitFieldData(instance, self.name)

    def __set__(self, instance, value):
        if isinstance(value, memoryview):
            value = value.tobytes()
        elif isinstance(value, bytearray):
            value = bytes(value)
        elif isinstance(value, BigBitFieldData):
            value = bytes(value._buffer)
        elif isinstance(value, str):
            value = value.encode('utf-8')
        elif not isinstance(value, bytes):
            raise ValueError('Value must be either a bytes, memoryview or '
                             'BigBitFieldData instance.')
        super(BigBitFieldAccessor, self).__set__(instance, value)


class BigBitField(BlobField):
    accessor_class = BigBitFieldAccessor

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default', bytes)
        super(BigBitField, self).__init__(*args, **kwargs)

    def db_value(self, value):
        return bytes(value) if value is not None else value
