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
    return [Change.from_bytes(data[i:i + 10]) for i in range(0, len(data), 10)]


@dataclass
class Change:
    """
    Each change in the state of the game is defined by this class.

    Attributes:
        curr (x, y, t): The current position and type of tile.
        next (x, y, t): The next position and type of tile.
    """
    uuid: str
    curr: Tuple[int, int, int]
    next: Tuple[int, int, int]

    @classmethod
    def from_bytes(cls, data: bytes) -> Change:
        """
        Creates a Change object from a byte array.
        """
        return cls(data[:4].decode('utf-8'), (data[4], data[5], data[6]), (data[7], data[8], data[9]))

    def to_bytes(self) -> bytes:
        """
        Converts the Change object to a byte array.
        """
        return self.uuid.encode('utf-8') + bytes(self.curr) + bytes(self.next)


@dataclass
class GameState:
    state: List[List[int]]
    players: Dict[int, Tuple[str, int, int]]
    lock: Lock
    mode: int = field(default=0)  # defaults to 0 for player, 1 for server
    player_status: Dict[str, bool] = field(default_factory=dict)

    def get_state(self) -> list[list[int]]:
        """Returns the state of the game.

        Returns:
            list[list[int]]: The state of the game.
        """
        return self.state

    def get_players(self) -> list[str]:
        """Returns the players of the game.

        Returns:
            dict: The players of the game.
        """
        return [player[0] for player in self.players.values()]

    def get_player_positions(self) -> Dict[str, Tuple[int, int]]:
        """Returns the positions of the players.

        Returns:
            dict: The positions of the players.
        """
        return {player[0]: (player[1], player[2]) for player in self.players.values()}

    @singledispatchmethod
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
                if not self.player_status.get(change.uuid):
                    continue
                else:
                    # TODO: apply changes to the gamestate
                    pass

    @apply_state.register
    def _(self, changes: list[Change]):
        """Applies the changes to the state of the game.

        Args:
            changes (list[Change]): The changes to be applied.
        """
        if self.mode == 0:
            # Player mode
            # Doesn't do any checks
            pass
        else:
            for change in changes:
                # if the player is not in the game/is dead, skip the change
                if not self.player_status.get(change.uuid):
                    continue
                else:
                    pass

    @apply_state.register
    def _(self, change: Change):
        """Applies the changes to the state of the game.

        Args:
            change (Change): The change to be applied.
        """
        pass


# TODO: implement test suite
