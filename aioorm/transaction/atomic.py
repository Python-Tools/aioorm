from aioorm.utils import _callable_context_manager
from .manual import _manual

class _atomic(_callable_context_manager):
    def __init__(self, db, lock_type=None):
        self.db = db
        self._lock_type = lock_type
        self._transaction_args = (lock_type,) if lock_type is not None else ()

    def __enter__(self):
        if self.db.transaction_depth() == 0:
            self._helper = self.db.transaction(*self._transaction_args)
        else:
            self._helper = self.db.savepoint()
            if isinstance(self.db.top_transaction(), _manual):
                raise ValueError('Cannot enter atomic commit block while in '
                                 'manual commit mode.')
        return self._helper.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._helper.__exit__(exc_type, exc_val, exc_tb)
