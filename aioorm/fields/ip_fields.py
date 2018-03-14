import struct
import socket
from .integer_fields import BigIntegerField


class IPField(BigIntegerField):
    def db_value(self, val):
        if val is not None:
            return struct.unpack('!I', socket.inet_aton(val))[0]

    def python_value(self, val):
        if val is not None:
            return socket.inet_ntoa(struct.pack('!I', val))
