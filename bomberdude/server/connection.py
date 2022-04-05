from common.uuid import uuid
from dataclasses import dataclass, field
from logging import Logger
from socket import socket, AF_INET6, SOCK_DGRAM
from typing import Tuple
import time


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
    last_kalive: int = field(default=0)
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

    def kalive(self):
        """
        Updates the last kalive time.
        """
        self.last_kalive = int(time.time())
        self.logger.debug('Updated last kalive time to {self.last_kalive}')

    def __str__(self) -> str:
        return f'{self.uuid} {self.name} {self.address}'

    def __repr__(self) -> str:
        return self.__str__()

# TODO: implement test suite
