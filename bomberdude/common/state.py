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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property, singledispatchmethod
import struct
from typing import Dict, List, Optional, Tuple
from threading import Lock
from .payload import ACTIONS, Payload
import time

FLOOR: int = 0
WALL: int = 1
BOMB: int = 2
EXPLOSION: int = 3
# TODO: Add more tiles.
# CRATE = 4
# ...
PLAYER_OFFSET: int = 10
PLAYER_1: int = 10
PLAYER_2: int = 11
PLAYER_3: int = 12
PLAYER_4: int = 13
PLAYER_1_DEAD: int = 20
PLAYER_2_DEAD: int = 21
PLAYER_3_DEAD: int = 22
PLAYER_4_DEAD: int = 23


state = [[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
         [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
         [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
         [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
         [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
         [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
         [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
         [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
         [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
         [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
         [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
         [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
         [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]]


def parse_payload(payload: Payload) -> List[Change] | None:
    """
    Parses the payload and returns the change list or message.
    If the payload is not a valid change list or message, it returns None.

    :param payload: The payload to parse.
    :return: The change list or message.
    """
    if payload.type == ACTIONS:
        if len(payload.data) > 6:
            # Create a list of changes from the payload's data.
            return change_from_bytes(payload.data)

    return None


def change_from_bytes(data: bytes) -> List[Change]:
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


def bytes_from_changes(lst: List[Change]) -> bytes:
    """
    Converts a list of changes to a byte array.

    :param list: The list of changes.
    :return: The byte array.
    """
    data: bytes = b''

    for c in lst:
        data += c.to_bytes()

    return data


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

    def unpack(self):
        """
        Unpacks the Change object to a tuple of the current and next position and type of tile.
        """
        return self.curr[2], self.curr[:2], self.next[2], self.next[:2]

    def to_bytes(self) -> bytes:
        """
        Converts the Change object to a byte array.
        """

        return bytes(self.curr) + bytes(self.next)


@dataclass
class GameState:
    """
    Game State

    Attributes:
        state (list[list[int]]): The state of the game.
        players (dict[int, tuple[int,int]]): The players of the game, {id: (x,y)}.
        bombs (dict[int, [float, int, int]]): The bombs of the gamem {id: (ts,x,y)}.
        mode (int): The mode that dictates how this class should behave.
    """
    lock: Lock
    players: Dict[int, Tuple[int, int]]  # {id: (x, y)}
    mode: int = field(default=0)  # defaults to 0 for player, 1 for server
    state: List[List[int]] = field(default_factory=lambda: state)
    bombs: Dict[int, Tuple[float, int, int]] = field(default_factory=dict)
    range: int = field(default=2)
    explosions: List[Explosion] = field(default_factory=list)

    def reset(self):
        """
        Resets the game state.
        """
        self.players = {
            0: (1, 1),
            1: (12, 1),
            2: (1, 12),
            3: (12, 12),
        }
        self.bombs = {}
        self.explosions = []

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

    def _apply_change(self, change: Change):
        """
        Applies a change to the state of the game.

        :param change: The change to apply.
        """
        x, y, t = change.curr
        _x, _y, _t = change.next
        self.state[y][x] = t
        self.state[_y][_x] = _t

    def _is_player(self, val: int, x: int, y: int) -> Optional[int]:
        """
        Checks if the value at the given position is a player.

        :param val: The value to check.
        :param x: The x coordinate of the tile.
        :param y: The y coordinate of the tile.
        """
        if val == PLAYER_1 and self.players[0] == (x, y):
            # this will notify the players that they are dead
            self.players[0] = (-1, -1)
            return PLAYER_1_DEAD
        if val == PLAYER_2 and self.players[1] == (x, y):
            # this will notify the players that they are dead
            self.players[1] = (-1, -1)
            return PLAYER_2_DEAD
        if val == PLAYER_3 and self.players[2] == (x, y):
            # this will notify the players that they are dead
            self.players[2] = (-1, -1)
            return PLAYER_3_DEAD
        if val == PLAYER_4 and self.players[3] == (x, y):
            # this will notify the players that they are dead
            self.players[3] = (-1, -1)
            return PLAYER_4_DEAD

        return None

    def _explosion(self, id: int, x: int, y: int) -> Dict[Tuple[int, int], int]:
        """
        This method shouldn't be called directly from outside this class.

        Explodes a bomb and recursively calls itself if it finds a bomb.
        An explosion is a cross of tiles with the bomb's range.


        :param id: The id of the bomb.
        :param x: The x position of the bomb.
        :param y: The y position of the bomb.
        :return: A list of tiles affected by the explosion. {id: (x,y)}
        """
        # remove the bomb from the bombs dictionary to prevent explosion loops
        self.bombs.pop(id)

        # get the tiles in the cross
        up = [self.state[x][y + 1], self.state[x][y + 2]]
        down = [self.state[x][y - 1], self.state[x][y - 2]]
        left = [self.state[x - 1][y], self.state[x - 2][y]]
        right = [self.state[x + 1][y], self.state[x + 2][y]]

        out: Dict[Tuple[int, int], int] = {}

        for i in range(0, self.range):
            if up[i] == WALL:
                break
            elif up[i] == BOMB:
                self._explosion(id, x, y + i)
            else:
                self._is_player(up[i], x, y + i)
                out[(x, y + i)] = EXPLOSION

        for i in range(0, self.range):
            if down[i] == WALL:
                break
            elif down[i] == BOMB:
                self._explosion(id, x, y - i)
            else:
                self._is_player(down[i], x, y - i)
                out[(x, y - i)] = EXPLOSION

        for i in range(0, self.range):
            if right[i] == WALL:
                break
            elif right[i] == BOMB:
                self._explosion(id, x + i, y)
            else:
                self._is_player(right[i], x + i, y)
                out[(x + i, y)] = EXPLOSION

        for i in range(0, self.range):
            if left[i] == WALL:
                break
            elif left[i] == BOMB:
                self._explosion(id, x - i, y)
            else:
                self._is_player(left[i], x - i, y)
                out[(x - i, y)] = EXPLOSION

        return out

    def _update_bombs(self) -> Explosion:
        """
        This method shouldn't be called directly from outside the class.

        Updates the bombs state.
        New bombs are added to the bombs dictionary.
        Exploded bombs are calculated and removed from the bombs dictionary.

        :param change: The change to apply to the bombs.
        """
        timestamp = time.time()

        out: Dict[Tuple[int, int], int] = {}

        # Remove exploded bombs from the bombs dictionary.
        for bomb_id, explosion in self.bombs.items():
            if explosion[0] + 3 < timestamp:
                out.update(self._explosion(
                    bomb_id, explosion[1], explosion[2]))

        return Explosion(out)

    def apply_state(self, data: bytes) -> List[Change]:
        """Applies the changes to the state of the game.

        :param data: The data to apply.
        :return (changes, List[Explosion]): The list of changes that were applied.
        """
        changes: List[Change] = change_from_bytes(data)
        outgoing: List[Change] = []

        if self.mode == 0:
            # Player mode
            # Doesn't do any checks, just applies the changes.
            for change in changes:
                self._apply_change(change)
        else:
            for change in changes:
                ctile, cur, ntile, nxt = change.unpack()

                # check whether the current tile corresponds to what we expect
                if ctile != self.state[cur[0]][cur[1]]:
                    # if not, discard the change
                    continue

                elif ctile == FLOOR and ntile == BOMB and cur == nxt:
                    # get the id of the bomb
                    bomb_id = len(self.bombs)
                    # add the bomb to the bombs dictionary
                    self.bombs[bomb_id] = (time.time(), cur[0], cur[1])
                    outgoing.append(change)

                elif cur == self.players[ctile - PLAYER_OFFSET]:
                    # player update
                    if adjacent(cur, nxt) and ntile == FLOOR:
                        # update the player position
                        self.players[ctile - PLAYER_OFFSET] = nxt
                        outgoing.append(change)
                    else:
                        # invalid move
                        # send the player back to the previous position
                        Change((cur[0], cur[1], ctile),
                               (cur[0], cur[1], ctile))
                else:
                    continue

        explosions = self._update_bombs()
        self.explosions.append(explosions)
        outgoing.extend(explosions.changes)

        # dead players changes
        # TODO: decide whether to send all players instead of just dead
        for i in range(0, 4):
            if self.players[i] == (-1, -1):
                outgoing.append(Change((-1, -1, PLAYER_OFFSET + i),
                                       (-1, -1, i)))

        return outgoing


@dataclass
class Explosion:
    tiles: Dict[Tuple[int, int], int]
    timestamp: float = field(default_factory=time.time)

    @property
    def is_over(self) -> bool:
        """
        An explosion lasts for 1 second.

        :return: Whether the explosion is over
        """
        if self.timestamp + 1 < time.time():
            return True
        return False

    @cached_property
    def changes(self) -> List[Change]:
        """
        Returns a list of changes for this explosion. 
        This value is cached for faster multiple calls.

        :return: A list of changes that should be applied to the state.
        """
        return [Change((t, pos[0], pos[1]), (t, pos[0], pos[1])) for pos, t in self.tiles.items()]

    def clear(self):
        """
        Clears the explosion, setting all tiles to Floor.
        This is used when the explosion is over to send to players.
        """
        for tile in self.tiles:
            self.tiles[tile] = FLOOR


def adjacent(cur: Tuple[int, int], nxt: Tuple[int, int]) -> bool:
    """
    Checks whether two tiles are adjacent.

    :param cur: The current tile.
    :param nxt: The next tile.
    :return: Whether the tiles are adjacent.
    """
    if cur[0] == nxt[0] and abs(cur[1] - nxt[1]) == 1:
        return True
    if cur[1] == nxt[1] and abs(cur[0] - nxt[0]) == 1:
        return True
    return False

# TODO: implement test suite
