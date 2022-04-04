from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from common.state import GameState
from .connection import Conn
from common.payload import ACTIONS, KALIVE, LEAVE, STATE, Payload
from common.state import Change, bytes_from_changes
from logging import Logger
from socket import AF_INET6, socket, SOCK_DGRAM
from threading import Thread, Lock
import time
from typing import Dict, List, Optional, Tuple
import json


@dataclass
class Lobby(Thread):
    """
    A Lobby is a thread that implements the basic game logic.
    A Lobby is a thread that is responsible for:
        - Accepting/Rejecting connections
        - Game logic
        - Handling incoming data
    """
    # lobby uuid
    uuid: str
    # socket used to receive data from clients
    sock: socket
    # max number of players allowed in the lobby
    capacity: int = field(default=4)
    # list of players currently present in the lobby
    conns: List[Conn] = field(init=False, default_factory=list)
    # list of actions that are yet to be handled
    action_queue_inbound: List[Payload] = field(
        init=False, default_factory=list)
    # list of actions that are yet to be sent
    action_queue_outbound: List[Change] = field(
        init=False, default_factory=list)
    # current state of the game
    game_state: GameState = field(init=False)
    # lock used to protect game state from multiple thread access
    game_state_lock: Lock = field(init=False)
    # flag to indicate whether the lobby has a running game
    in_game: bool = field(init=False, default=False)
    # logger used to log messages to the console
    logger: Logger = field(init=False)
    # flag to indicate whether the lobby is running
    running: bool = field(init=False, default=False)

    def __post_init__(self):
        """
        This method should not be called directly.

        Method that is called after the lobby has been initialized.
        """
        self.game_state_lock = Lock()
        self.game_state = GameState(self.game_state_lock, {})
        # TODO: is this necessary
        # super(Lobby, self).__init__()
        self.logger = Logger('Lobby')
        self.logger.info('Lobby post init\'d')

    def add_player(self, conn: Conn) -> bool:
        """
        Adds a conn to the lobby.

        :param conn: The conn to be added.
        """
        if self.is_full:
            self.logger.info(
                'Lobby is fully, cannot add conn, {conn}')
            return False

        # check whether the connection already exists
        for c in self.conns:
            if c.address == conn.address:
                self.logger.info(
                    'Connection already exists, {conn}')
                return False

        self.conns.append(conn)
        self.logger.info('Added conn to lobby, {conn}')
        return True

    def get_player(self, addr: Tuple[str, int]) -> Optional[Conn]:
        """
        Gets a conn from the lobby.

        :param addr: The address of the conn to be retrieved.
        """
        for c in self.conns:
            if c.address == addr:
                return c
        return None

    def remove_player(self, conn) -> bool:
        """
        Removes a conn from the lobby.

        :param conn: The conn to be removed.
        """
        if conn not in self.conns:
            self.logger.info(
                'Connection not found, {conn}')
            return False

        self.conns.remove(conn)
        self.logger.info('Removed conn from lobby, {conn}')
        return True

    @ property
    def is_full(self) -> bool:
        """
        Returns True if the lobby is full.
        """
        if len(self.conns) == self.capacity:
            return True
        else:
            return False

    @ property
    def is_empty(self) -> bool:
        """
        Returns True if the lobby is empty.
        """
        if len(self.conns) == 0:
            return True
        else:
            return False

    @property
    def address(self) -> Tuple[str, int]:
        """
        Fetches the ip address of the lobby.

        Returns:
            The address of the lobby.
        """
        return self.sock.getsockname()

    @property
    def ip(self) -> str:
        """
        Fetches the ip address of the lobby.
        """
        return self.sock.getsockname()[0]

    @property
    def port(self) -> int:
        """
        Fetches the port of the lobby.
        """
        return self.sock.getsockname()[1]

    # TODO: Find out how ipv6 will affect this
    def unicast(self, data: bytes, conn: Conn):
        """
        Sends data to a conn in the lobby.

        :param data: The data to be sent.
        :param conn: The conn to be sent to.
        """
        if conn not in self.conns:
            raise ValueError('Connection not found')

        conn.send(data)

    # TODO: Find out how ipv6 will affect this
    def multicast(self, data: bytes, blacklist: Optional[Conn] = None):
        """
        Sends data to all conns in the lobby.

        :param data: The data to be sent.
        """
        # get all conns excluding the blacklist
        conns = [c for c in self.conns if c != blacklist]

        # send data to all conns

        for c in conns:
            c.send(data)

    def _handle_incoming_data(self):
        """
        This method should not be called directly.

        Method that will run in a separate thread to handle incoming data.
        """
        while self.running:
            time.sleep(0.001)

            try:
                data, addr = self.sock.recvfrom(1024)

                # get the conn that sent the data
                conn = self.get_player(addr)

                if conn is None:
                    # TODO: Change this later for NDN redirect support
                    self.logger.debug('Connection not found, {conn}')
                    continue

                # parse the data
                payload = Payload.from_bytes(data)

                # If the payload's sequence number is equal or older than the current one, discard
                if payload.seq_num <= conn.seq_num:
                    self.logger.debug('Sequence number is older, {conn}')
                    continue

                # If it's an action, append it to the action queue
                if payload.type == ACTIONS:
                    with self.game_state_lock:
                        self.action_queue_inbound.append(payload)
                    self.logger.debug(
                        'Appended action to action queue, {conn}')

                elif payload.type == LEAVE:
                    try:
                        self.remove_player(conn)
                        self.logger.debug(
                            'Removed conn from lobby, {conn}', conn)
                    except ValueError:
                        self.logger.error(
                            'Attempt to remove unexistent connection, {conn}', conn)

                elif payload.type == KALIVE:
                    conn.kalive()

                else:
                    # Unhandled payload type
                    self.logger.error(
                        'Unhandled payload type, {payload.type}', payload.type)

            except Exception as e:
                self.logger.error('Error in _handle_incoming_data, {e}')

    def _handle_connection_timeouts(self):
        """
        This method should not be called directly.

        Method that will run in a separate thread to handle connection timeouts.
        """
        while self.running:
            conns = [c for c in self.conns if c.last_kalive < time.time() - 10]
            map(self.remove_player, conns)
            time.sleep(1)

    def _handle_game_state_changes(self):
        """
        This method should not be called directly.

        Method that will run in a separate thread to handle game state changes.
        """
        while self.running:
            while not self.is_full:
                # wait until the lobby is full to start the game
                time.sleep(0.03)

            self.in_game = True
            self.game_state.reset()

            __data: Dict[int, Dict[str, int | float | str]] = {}
            start_time = time.time()

            # send each conn it's player number
            for i, c in enumerate(self.conns):
                __data[i] = {
                    "id": i,
                    "time": start_time
                }

            while start_time + 5 > time.time():
                for i, c in enumerate(self.conns):
                    p = __data[i]
                    __data[i]['uuid'] = c.uuid
                    data_bytes = json.dumps(p).encode('utf-8')
                    payload = Payload(STATE, data_bytes, self.uuid, c.uuid, 0)
                    c.send(payload.to_bytes())
                time.sleep(0.05)

            while self.in_game:
                _incoming_changes = []

                with self.game_state_lock:
                    _incoming_changes = self.action_queue_inbound
                    self.action_queue_inbound = []

                # Unpack all incoming changes
                for payload in _incoming_changes:
                    changes = payload.data

                    updates = self.game_state.apply_state(changes)
                    # append updates to the outgoing queue
                    self.action_queue_outbound.extend(updates)

                time.sleep(0.03)

    def _handle_outgoing(self):
        """
        This method should not be called directly.

        Method running in a separate thread to handle outgoing data.
        The data to be sent is taken from the outbound action queue.
        """
        while self.running:
            actions = []
            with self.game_state_lock:
                actions = self.action_queue_outbound
                self.action_queue_outbound = []

            # convert actions to bytes
            data = bytes_from_changes(actions)

            for c in self.conns:
                c.send(data)

            time.sleep(0.001)

    def run(self):
        """
        Game server main loop.

        This method spawns a threadpool to handle certain tasks.
        Tasks are:
        - Connection timeouts
        - Game state changes
        - Incoming data
        - Outgoing data
        """
        self.running = True

        self.logger.info('Lobby started')

        with ThreadPoolExecutor(max_workers=3) as executor:
            executor.submit(self._handle_connection_timeouts)
            executor.submit(self._handle_game_state_changes)
            executor.submit(self._handle_incoming_data)
            # executor.submit(self._handle_outgoing)
            executor.shutdown(wait=True)

    def terminate(self):
        """
        Terminates the lobby.
        """
        self.logger.info('Terminating lobby')
        self.running = False
        self.in_game = False


# TODO: Implement test suite
