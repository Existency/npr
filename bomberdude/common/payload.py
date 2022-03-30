from __future__ import annotations
from dataclasses import dataclass, field
import struct

# Payload types
ACCEPT = 0x01
REJECT = 0x02
HELLO = 0x03
LEAVE = 0x04
ACK = 0x04
JOIN = 0x05
ACTIONS = 0x06
STATE = 0x07
PING = 0x08
PONG = 0x09
ERROR = 0x0A


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
        data (n Bytes): The data to be sent, variable length.
    """
    type: int
    data: bytes
    length: int = field(init=False)
    lobby_uuid: str
    player_uuid: str
    seq_num: int

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
        try:
            type, length, lobby, player, seq_num = struct.unpack(
                '!Bl4s4sl', data[:17])
        except struct.error:
            raise ValueError('Invalid payload')
        except Exception as e:
            raise e

        return cls(type, data[17:length+17], lobby, player, seq_num)

    def to_bytes(self) -> bytes:
        """
        Converts the payload to a byte array.

        : return: The byte array representation of the payload.
        """
        return struct.pack(
            '!Bl4s4sl',
            self.type,
            self.length,
            self.lobby_uuid.encode('utf-8'),
            self.player_uuid.encode('utf-8'),
            self.seq_num
        ) + self.data
