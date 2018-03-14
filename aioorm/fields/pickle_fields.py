import pickle
from .blob_fields import BlobField


class PickleField(BlobField):
    def python_value(self, value):
        if value is not None:
            if isinstance(value, memoryview):
                value = bytes(value)
            return pickle.loads(value)

    def db_value(self, value):
        if value is not None:
            pickled = pickle.dumps(value, pickle.HIGHEST_PROTOCOL)
            return self._constructor(pickled)
