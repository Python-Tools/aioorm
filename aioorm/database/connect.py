from aioorm.utils import _callable_context_manager


class _ConnectionState:
    def __init__(self, **kwargs):
        super(_ConnectionState, self).__init__(**kwargs)
        self.reset()

    def reset(self):
        self.closed = True
        self.conn = None
        self.transactions = []

    def set_connection(self, conn):
        self.conn = conn
        self.closed = False


class _ConnectionLocal(_ConnectionState, threading.local):
    pass


class _NoopLock:
    __slots__ = ()

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


class ConnectionContext(_callable_context_manager):
    __slots__ = ('db',)

    def __init__(self, db):
        self.db = db

    def __enter__(self):
        if self.db.is_closed():
            self.db.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()
