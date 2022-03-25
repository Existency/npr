from typing import Tuple
from socket import socket, AF_INET6, SOCK_DGRAM
from uuid import uuid4
from logging import Logger


class Conn:
    # TODO: Should this be threaded?
    """
    A connection to a client, used for sending data to the client.
    """
    name: str
    seq_num: int
    uuid: str
    address: Tuple[str, int]
    sock: socket
    logger: Logger

    def __init__(self, name: str, address: Tuple[str, int]):
        self.uuid = str(uuid4())
        self.address = address
        self.name = name
        self.seq_num = 0
        self.logger = Logger('Connection {self.uuid}')
        self.logger.info('Connection {self.uuid} init\'d')

    def send(self, data: bytes):
        """
        Sends packet to client.
        """
        self.logger.debug('Sending packet, {data}, to client {self.uuid}')
        sock = socket(AF_INET6, SOCK_DGRAM)
        sock.sendto(data, self.address)
