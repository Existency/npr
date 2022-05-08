from __future__ import annotations
from dataclasses import dataclass, field
import struct


# These serve as the list of available payload types.
# Connection types
ACCEPT = 0x01
REJECT = 0x02
JOIN = 0x03
REJOIN = 0x04
LEAVE = 0x05
REDIRECT = 0x06  # redirect payload to another host, implies an extension to the header
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
    REDIRECT: 'REDIRECT',
    ERROR: 'ERROR',
    KALIVE: 'KALIVE',
    ACK: 'ACK',
    ACTIONS: 'ACTIONS',
    STATE: 'STATE'
}


def get_payload_type(val: int) -> str:
    """
    Retrieves the payload type str representation from the integer value.

    :param val: The integer value to convert.
    :return: The payload type str representation.
    """
    return ptypes.get(val, 'UNKNOWN')


@dataclass
class Payload:
    """
    Payload used to communicate between the server and the client.
    A payload has an overhead of 17 bytes.

    Attributes:
        type (1 Byte): The type of payload (action).
        lobby (4 Bytes): The lobby uuid.
        length (4 Bytes): The length of the payload.
        player (4 Bytes): The player uuid.
        seq_num (4 Bytes): The sequence number of the packet.
        ttl (1 Byte): The time to live of the packet, capped at 3.
        data (n Bytes): The data to be sent, variable length.
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
    ttl: int = field(default=3)
    """The time to live of the packet, capped at 3. (1 Byte)"""
    # TODO: Include the addresses of destination and source nodes.

    def __post_init__(self):
        self.length = len(self.data)

    def __lt__(self, other: Payload) -> bool:
        return self.seq_num < other.seq_num

    def __gt__(self, other: Payload) -> bool:
        return self.seq_num > other.seq_num

    def __eq__(self, other) -> bool:
        """
        For two payloads to be equal they must have all the same attributes.
        """
        return (self.type == other.type
                and self.length == other.length
                and self.lobby_uuid == other.lobby
                and self.player_uuid == other.player
                and self.seq_num == other.seq_num
                and self.data == other.data)

    @classmethod
    def from_bytes(cls, data: bytes) -> Payload:
        """
        Creates a Payload from a byte array.

        : param data: The byte array to create the Payload from.
        : return: The Payload created from the byte array.
        """
        header = data[:17]
        try:
            type, length, lobby, player, seq_num = struct.unpack(
                '!Bl4s4sl', header)

            return cls(type, data[17: length+17], lobby.decode(), player.decode(), seq_num)

        except Exception as e:
            raise ValueError(e.__repr__())

    def to_bytes(self) -> bytes:
        """
        Converts the payload to a byte array.

        : return: The byte array representation of the payload.
        """

        lobby_bytes = bytes(self.lobby_uuid, 'utf-8')
        player_bytes = bytes(self.player_uuid, 'utf-8')

        return struct.pack(
            '!Bl4s4sl',
            self.type,
            self.length,
            lobby_bytes,
            player_bytes,
            self.seq_num
        ) + self.data
