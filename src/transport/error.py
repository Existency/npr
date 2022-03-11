class SocketError(Exception):
    def __init__(self, err):
        self.error = err

    def __str__(self) -> str:
        return repr(self.error)
