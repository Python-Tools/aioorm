from aioorm.utils import _callable_context_manager


class _manual(_callable_context_manager):
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        top = self.db.top_transaction()
        if top and not isinstance(self.db.top_transaction(), _manual):
            raise ValueError('Cannot enter manual commit block while a '
                             'transaction is active.')
        self.db.push_transaction(self)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.db.pop_transaction() is not self:
            raise ValueError('Transaction stack corrupted while exiting '
                             'manual commit block.')
