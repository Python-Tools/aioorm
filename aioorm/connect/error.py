class ConnectError(Exception):
    pass

class NotConnectYet(ConnectError):
    pass


class InvalidURI(Exception):
    pass