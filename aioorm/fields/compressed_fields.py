import bz2
import zlib
from .blob_fields import BlobField


class CompressedField(BlobField):
    ZLIB = 'zlib'
    BZ2 = 'bz2'
    algorithm_to_import = {
        ZLIB: zlib,
        BZ2: bz2,
    }

    def __init__(self, compression_level=6, algorithm=ZLIB, *args,
                 **kwargs):
        self.compression_level = compression_level
        if algorithm not in self.algorithm_to_import:
            raise ValueError('Unrecognized algorithm %s' % algorithm)
        compress_module = self.algorithm_to_import[algorithm]
        if compress_module is None:
            raise ValueError('Missing library required for %s.' % algorithm)

        self.algorithm = algorithm
        self.compress = compress_module.compress
        self.decompress = compress_module.decompress
        super(CompressedField, self).__init__(*args, **kwargs)

    def python_value(self, value):
        if value is not None:
            return self.decompress(value)

    def db_value(self, value):
        if value is not None:
            return self._constructor(
                self.compress(value, self.compression_level))
