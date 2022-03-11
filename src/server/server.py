from typing import Optional
from threading import Thread
from transport.base import Connection


class Server:
    instream: Optional[Connection]
    oustreams: list[Connection]

    def __init__(self, port: int = 8888):
        """
        Initializes the server.

        :param port: port number, defaults to 8888
        """
        try:
            self.instream = Connection()
            self.instream.connect('', port)
            self.oustreams = []
        except Exception as e:
            print("Error, can't create server:", e)
            exit(1)

    def accept_client(self, client: Connection):
        """
        Accepts a new client, adding it to the outstreams list.

        :param client: client connection to be added
        """
        self.oustreams.append(client)

    def run(self):
        """
        Main loop of the server.
        """
        # Game loop goes brrrr

        pass


if __name__ == '__main__':
    server = Server()
    server.run()
