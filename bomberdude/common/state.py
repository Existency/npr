"""
The state of the game, it's methods and attributes are defined in this module.

    Attributes:
        state (dict): The state of the game.
        players (dict): The players of the game.

    Methods:
        get_state(self): Returns the state of the game.
        get_players(self): Returns the players of the game.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from functools import singledispatchmethod
import struct
from typing import Dict, List, Optional, Tuple
from threading import Lock
from .payload import ACTIONS, Payload


class Tiles(Enum):
    FLOOR = 0
    WALL = 1
    PLAYER_1 = 2
    PLAYER_2 = 3
    PLAYER_3 = 4
    PLAYER_4 = 5
    BOMB = 6
    # TODO: Add more tiles.
    # CRATE = 7


state = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 2, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 3, 1],
    [1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1],
    [1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1],
    [1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1],
    [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
    [1, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1],
    [1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 1],
    [1, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0, 1, 0, 1],
    [1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1],
    [1, 4, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 5, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
]


def parse_payload(payload: Payload) -> List[Change] | str | None:
    """
    Parses the payload and returns the change list or message.
    If the payload is not a valid change list or message, it returns None.

    :param payload: The payload to parse.
    :return: The change list or message.
    """
    if payload.type == ACTIONS:
        if len(payload.data) > 10:
            # Create a list of changes from the payload's data.
            return change_list(payload.data)
        return None

    if payload.data:
        # Return the message.
        return payload.data.decode('utf-8')

    return None


def change_list(data: bytes) -> List[Change]:
    """
    Converts a byte array to a list of Change objects.
    """
    # apply Change(data[i:i + 6]) to each i in range(0, len(data), 6), use a map
    # use a list comprehension to map the result of the map to a list of Change objects
    # if the constructor returns None, discard the change
    # return the list of changes
    changes = []

    for i in range(0, len(data), 6):
        change = Change.from_bytes(data[i:i + 6])
        if change:
            changes.append(change)

    return changes


@dataclass
class Change:
    """
    Each change in the state of the game is defined by this class.

    Attributes:
        curr (x, y, t): The current position and type of tile.
        next (x, y, t): The next position and type of tile.
    """
    curr: Tuple[int, int, int]
    next: Tuple[int, int, int]

    @classmethod
    def from_bytes(cls, data: bytes) -> Change | None:
        """
        Creates a Change object from a byte array.
        """
        try:
            x, y, t = struct.unpack('!BBB', data[:3])
            _x, _y, _t = struct.unpack('!BBB', data[3:6])
            return Change((x, y, t), (_x, _y, _t))
        except struct.error:
            return None

    def to_bytes(self) -> bytes:
        """
        Converts the Change object to a byte array.
        """

        return bytes(self.curr) + bytes(self.next)


@dataclass
class GameState:
    lock: Lock
    players: Dict[int, Tuple[int, int]]  # {id: (x, y)}
    state: List[List[int]] = field(default_factory=lambda: state)
    mode: int = field(default=0)  # defaults to 0 for player, 1 for server
    player_status: Dict[str, bool] = field(default_factory=dict)

    def get_state(self) -> list[list[int]]:
        """Returns the state of the game.

        Returns:
            list[list[int]]: The state of the game.
        """
        return self.state

    def get_players(self) -> list[int]:
        """Returns the players of the game.

        Returns:
            dict: The players of the game.
        """
        return list(self.players.keys())

    def get_player_positions(self) -> Dict[int, Tuple[int, int]]:
        """Returns the positions of the players.

        Returns:
            dict: The positions of the players.
        """
        return self.players

    def apply_state(self, data: bytes):
        """Applies the changes to the state of the game.

        Args:
            changes (list[Change]): The changes to be applied.
        """
        changes: List[Change] = change_list(data)

        if self.mode == 0:
            # Player mode
            # Doesn't do any checks
            pass
        else:
            for change in changes:
                # if the player is not in the game/is dead, skip the change
                pass


# TODO: implement test suite
