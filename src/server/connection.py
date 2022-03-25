from typing import Tuple
from socket import socket, AF_INET6, SOCK_DGRAM
from uuid import uuid4


class Conn:
    # TODO: Should this be threaded?
    """
    A connection to a client, used for sending data to the client.
    """
    name: str
    uuid: str
    address: Tuple[str, int]
    sock: socket

    def __init__(self, name: str, address: Tuple[str, int]):
        self.uuid = str(uuid4())
        self.address = address

    def send(self, data: bytes):
        """
        Sends packet to client.
        """
        # TODO: Should we keep this socket open?
        sock = socket(AF_INET6, SOCK_DGRAM)
        sock.sendto(data, self.address)
