from __future__ import annotations
import struct
from dataclasses import dataclass
from common.payload import Payload
from common.types import NDNPacketType, Prefix


pattern = '!Bl'
"""
    The pattern used to (un)pack the payload.

    The format is:
    - !: Network Byte order(Big endian)
    - B: The payload type.              (1 byte)
    - l: The prefix's length.          (4 bytes)
    ----------------------------------------------
    Total:                               5 bytes
"""

OFFSET = 5  # 1 + 4 = 5
"""The header's offset in bytes."""


@dataclass
class NDNPacket:
    """
    The NDN Packet is the base class for both types of NDN packets.
        - type: The type of the packet.
        - name: The name of the packet.
        - payload: The payload of the packet.
    """
    type: NDNPacketType
    name: Prefix
    payload: Payload

    def __hash__(self) -> int:
        return super().__hash__()

    def get_name(self) -> str:
        """
        Retrieves the name of the packet.
        """
        return self.name

    def get_source_address(self) -> str:
        """
        Retrieves the source address of the packet.
        """
        return self.payload.short_source

    def get_destination_address(self) -> str:
        """
        Retrieves the destination address of the packet.
        """
        return self.payload.short_destination

    def get_lobby_uuid(self) -> str:
        """
        Retrieves the lobby uuid of the packet.
        """
        return self.payload.lobby_uuid

    def get_player_uuid(self) -> str:
        """
        Retrieves the player uuid of the packet.
        """
        return self.payload.player_uuid

    def to_bytes(self) -> bytes:
        """
        Converts the packet to a byte array.
        """
        name_bytes = bytes(self.name, 'utf-8')
        payload_bytes = self.payload.to_bytes()

        return struct.pack(
            pattern,
            self.type,
            len(payload_bytes)) + name_bytes + payload_bytes

    @classmethod
    def from_bytes(cls, data: bytes) -> NDNPacket:
        """
        Creates a NDN Packet from a byte array.

        :param data: The byte array to create the NDN Packet from.
        :return: The NDN Packet created from the byte array.
        """
        header = data[:OFFSET]

        try:
            type, length = struct.unpack(pattern, header)

            name = data[OFFSET: length+OFFSET].decode('utf-8')
            payload = Payload.from_bytes(data[length+OFFSET:])

            return cls(type, name, payload)

        except Exception as e:
            raise ValueError(e.__repr__())
