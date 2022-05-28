from __future__ import annotations
from dataclasses import dataclass, field
from functools import cached_property
import struct
from ipaddress import ip_address


# These serve as the list of available payload types.
# Connection types
ACCEPT = 0x01
REJECT = 0x02
JOIN = 0x03
REJOIN = 0x04
LEAVE = 0x05
REDIRECT = 0x06  # TODO: Deprecate this functionality.
ERROR = 0xA0
# Utility types
KALIVE = 0xC0
ACK = 0xC1
# Game types
ACTIONS = 0xD0
STATE = 0xD1

ptypes = {
    ACCEPT: 'ACCEPT',
    REJECT: 'REJECT',
    JOIN: 'JOIN',
    REJOIN: 'REJOIN',
    LEAVE: 'LEAVE',
    REDIRECT: 'REDIRECT',  # TODO: Deprecate this functionality.
    ERROR: 'ERROR',
    KALIVE: 'KALIVE',
    ACK: 'ACK',
    ACTIONS: 'ACTIONS',
    STATE: 'STATE'
}

pattern: str = '!Bl4s4slB16s16s'
"""
    The pattern used to (un)pack the payload.

    The format is:
    - !: Network Byte order(Big endian)
    - B: The payload type.              (1 byte)
    - l: The payload's length.          (4 bytes)
    - 4s: The lobby's uuid.             (4 bytes)
    - 4s: The player's uuid.            (4 bytes)
    - l: The payload's seqnum.          (4 bytes)
    - B: The payload's ttl.             (1 byte)
    - 16s: The payload's source.         (16 bytes)
    - 16s: The payload's destination.    (16 bytes)
    ----------------------------------------------
    Total:                               50 bytes
"""

OFFSET: int = 50  # 1 + 4 + 4 + 4 + 4 + 1 + 16 + 16
"""The header's offset in bytes."""


@dataclass
class Payload:
    """
    Payload used to communicate between the server and the client.
    A payload has an overhead of OFFSET bytes.

    Attributes:
        type (1 Byte): The type of payload (action).
        lobby (4 Bytes): The lobby uuid.
        length (4 Bytes): The length of the payload.
        player (4 Bytes): The player uuid.
        seq_num (4 Bytes): The sequence number of the packet.
        ttl (1 Byte): The time to live of the packet, capped at 3.
        source (16 Bytes): The source of the packet.
        destination (16 Bytes): The destination of the packet.
        data (variable): The payload's data.
    """
    type: int
    """The type of payload (action). (1 Byte)"""
    data: bytes
    """The data to be sent, variable length. (n Bytes)"""
    length: int = field(init=False)
    """The length of the payload. (4 Bytes)"""
    lobby_uuid: str
    """The lobby uuid. (4 Bytes)"""
    player_uuid: str
    """The player uuid. (4 Bytes)"""
    seq_num: int
    """The sequence number of the packet. (4 Bytes)"""
    source: bytes
    """The source of the payload. (16 Bytes)"""
    destination: bytes
    """The destination of the payload. (16 Bytes)"""
    ttl: int = field(default=3)
    """The time to live of the packet, capped at 3. (1 Byte)"""
    # TODO: Include the addresses of destination and source nodes.

    def __post_init__(self):
        self.length = len(self.data)

    def __lt__(self, other: Payload) -> bool:
        return self.seq_num < other.seq_num

    def __gt__(self, other: Payload) -> bool:
        return self.seq_num > other.seq_num

    @property
    def type_str(self) -> str:
        """
        Retrieves the payload type str representation.
        """
        return ptypes.get(self.type, 'UNKNOWN')

    @cached_property
    def is_accept(self) -> bool:
        """
        Checks if the payload has an accept type.
        """
        return self.type == ACCEPT

    @cached_property
    def is_reject(self) -> bool:
        """
        Checks if the payload has a reject type.
        """
        return self.type == REJECT

    @cached_property
    def is_join(self) -> bool:
        """
        Checks if the payload has a join type.
        """
        return self.type == JOIN

    @cached_property
    def is_rejoin(self) -> bool:
        """
        Checks if the payload has a rejoin type.
        """
        return self.type == REJOIN

    @cached_property
    def is_leave(self) -> bool:
        """
        Checks if the payload has a leave type.
        """
        return self.type == LEAVE

    @cached_property
    def is_redirect(self) -> bool:
        """
        Checks if the payload has a redirect type.
        """
        return self.type == REDIRECT

    @cached_property
    def is_error(self) -> bool:
        """
        Checks if the payload has an error type.
        """
        return self.type == ERROR

    @cached_property
    def is_kalive(self) -> bool:
        """
        Checks if the payload is a kalive.

        :return: True if the payload has a kalive type.
        """
        return self.type == KALIVE

    @cached_property
    def is_ack(self) -> bool:
        """
        Checks if the payload is an ack.

        :return: True if the payload has an ack type.
        """
        return self.type == ACK

    @cached_property
    def is_actions(self) -> bool:
        """
        Checks if the payload is an actions.

        :return: True if the payload has an actions type.
        """
        return self.type == ACTIONS

    @cached_property
    def is_state(self) -> bool:
        """
        Checks if the payload is a state.

        :return: True if the payload has a state type.
        """
        return self.type == STATE

    @cached_property
    def short_destination(self) -> str:
        """
        Retrieves the short representation of the destination.
        """
        return ip_address(self.destination).compressed

    @cached_property
    def short_source(self) -> str:
        """
        Retrieves the short representation of the source.
        """
        return ip_address(self.source).compressed

    @classmethod
    def from_bytes(cls, data: bytes) -> Payload:
        """
        Creates a Payload from a byte array.

        :param data: The byte array to create the Payload from.
        :return: The Payload created from the byte array.
        """
        header = data[:OFFSET]
        try:
            type, length, lobby, player, seq_num, ttl, source, destination = struct.unpack(
                pattern, header)

            return cls(type, data[OFFSET: length+OFFSET], lobby.decode(), player.decode(), seq_num, ttl, source, destination)

        except Exception as e:
            raise ValueError(e.__repr__())

    def to_bytes(self) -> bytes:
        """
        Converts the payload to a byte array.

        :return: The byte array representation of the payload.
        """

        lobby_bytes = bytes(self.lobby_uuid, 'utf-8')
        player_bytes = bytes(self.player_uuid, 'utf-8')

        return struct.pack(
            pattern,
            self.type,
            self.length,
            lobby_bytes,
            player_bytes,
            self.seq_num,
            self.ttl,
            self.source,
            self.destination
        ) + self.data
