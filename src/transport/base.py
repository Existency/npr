from ipaddress import IPv6Address
from socket import socket, AF_INET6, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR, error as serror
from typing import Optional
# from threading import Thread
import zlib
import _pickle as pickle

from transport.error import SocketError

# TODO: implement threading


class Connection():
    """
    Client network interface using IPv6.
    Runs in a separate thread and feeds the main thread with data.
    """
    csocket: Optional[socket]

    def __init__(self):
        # Thread.__init__(self)
        pass

    def connect(self, host: str, port: int):
        """
        Establish a connection with the server.

        :param host: host IP
        :param port: port number
        """
        try:
            self.csocket = socket(AF_INET6, SOCK_DGRAM)
            self.csocket.connect((host, port))

        except serror as e:
            raise SocketError(e)

    def send(self, socket, data: bytes):
        """
        Sends compressed data through the socket.
        The first 2 bytes are the length of the data.

        :param data: data to be sent
        """
        data = zlib.compress(pickle.dumps(data))
        data = len(data).to_bytes(2, byteorder='big') + data

        if self.csocket is None:
            raise SocketError("Client not connected")

        try:
            self.csocket.send(data)
        except serror as e:
            raise SocketError(e)

    def receive(self) -> bytes:
        """
        Receives compressed data through the socket.

        :return: data received
        """
        if self.csocket is None:
            raise SocketError("Client not connected")

        try:
            data, _addr = self.csocket.recvfrom(1024)
        except:
            raise SocketError("Connection closed")

        data = data[2:]
        data = pickle.loads(zlib.decompress(data))
        return data

    def disconnect(self):
        """
        Closes this connection.
        """
        if self.csocket is None:
            raise SocketError("Client not connected")

        self.csocket.close()
        self.csocket = None


# TODO: implement threading
class UDPServer():
    sock: Optional[Connection] = None
    terminate: bool = False
    players: list[Connection] = []

    def __init__(self, port: int = 8888):
        """
        Initializes the server.

        :param port: port number, defaults to 8888
        """
        try:
            self.sock = Connection()
            self.sock.connect('', port)
        except serror as e:
            raise SocketError(e)

    def run(self):
        """
        Main server loop.
        This server allows only one game at a time, up to 4 players per game.
        """
        while not self.terminate:
            #
            pass

    def accept_client(self, client: Connection):
        """
        Accepts a new client, adding it to the outstreams list.

        :param client: client connection to be added
        """
        self.players.append(client)

    def disconnect_client(self, client: Connection):
        """
        Disconnects a client from the server.

        :param client: client connection to be removed
        """
        self.players.remove(client)
