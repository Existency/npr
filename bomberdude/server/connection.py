from ipaddress import ip_address
from common.types import DEFAULT_PORT
from common.uuid import uuid
from dataclasses import dataclass, field
from logging import Logger
from socket import socket
from typing import Tuple
import time
import struct


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
    byte_address: bytes
    """The bytes representation of the address."""

    name: str
    """The name of the connection."""

    last_kalive: float
    """The time of  the last kalive."""

    address: Tuple[str, int] = field(init=False)
    """The address of the client."""

    logger: Logger = field(init=False)
    """The logger for the connection."""

    seq_num: int = field(default=0, init=False)
    """The sequence number of the connection."""

    uuid: str = field(init=False)
    """The unique id of the connection."""

    lobby_uuid: str = field(init=False, default='')
    """The lobby uuid."""

    def __hash__(self) -> int:
        """
        A connection's hash is calculated using it's uuid
        """
        return hash(self.uuid)

    @property
    def timed_out(self) -> bool:
        """
        Checks whether the connection has timed out.

        :return: True if the connection has timed out, False otherwise.
        """
        return int(time.time()) - self.last_kalive > 5

    def __post_init__(self):
        test2 = struct.unpack('!8H',self.byte_address)
        string_ints = [str(int) for int in test2]
        test2 = ':'.join(string_ints)

        self.address = (ip_address(test2).compressed, DEFAULT_PORT)
        print("Connection self.address",self.address)
        self.uuid = uuid()
        self.logger = Logger('Connection {self.uuid}')
        self.logger.info('Connection {self.uuid} init\'d')

    def send(self, data: bytes, sock: socket):
        """
        Sends packet to client.
        """
        self.logger.debug('Sending packet, {data}, to client {self.uuid}')
        return sock.sendto(data, self.address)

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
