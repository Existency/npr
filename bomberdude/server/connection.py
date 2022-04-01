from logging import Logger
from typing import Tuple
from dataclasses import dataclass, field
from socket import socket, AF_INET6, SOCK_DGRAM
from bomberdude.common.uuid import uuid


@dataclass
class Conn:
    """
    A connection to a client, used for sending data to the client.

    Attributes:
        address: The address of the client.
        uuid: The unique id of the connection.
        name: The name of the connection.
        seq_num: The sequence number of the connection.
        logger: The logger for the connection.
    """
    address: Tuple[str, int]
    name: str
    logger: Logger = field(init=False)
    seq_num: int = field(default_factory=int)
    uuid: str = field(init=False)
    # sock: socket = field(init=False)

    def __post_init__(self):
        self.uuid = uuid()
        self.logger = Logger('Connection {self.uuid}')
        self.logger.info('Connection {self.uuid} init\'d')

    def send(self, data: bytes):
        """
        Sends packet to client.
        """
        self.logger.debug('Sending packet, {data}, to client {self.uuid}')
        sock = socket(AF_INET6, SOCK_DGRAM)
        sock.sendto(data, self.address)

# TODO: implement test suite
