from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from bomberdude.common.state import GameState
from .connection import Conn
from common.payload import ACTIONS, KALIVE, LEAVE, Payload
from logging import Logger
from socket import AF_INET6, socket, SOCK_DGRAM
from threading import Thread, Lock
import time
from typing import List, Optional, Tuple


class Lobby(Thread):
    """
    A Lobby is a thread that implements the basic game logic.
    A Lobby is a thread that is responsible for:
        - Accepting/Rejecting connections
        - Game logic
        - Handling incoming data
    """
    # max number of players allowed in the lobby
    capacity: int
    # list of players currently present in the lobby
    conns: list
    # list of actions that are yet to be handled
    action_queue_inbound: List[Payload]
    # list of actions that are yet to be sent
    action_queue_outbound: list
    # current state of the game
    game_state: GameState
    # lock used to protect game state from multiple thread access
    game_state_lock: Lock
    # flag to indicate whether the lobby has a running game
    in_game: bool
    # logger used to log messages to the console
    logger: Logger
    # flag to indicate whether the lobby is running
    running: bool
    # socket used to receive data from clients
    sock: socket
    # lobby uuid
    uuid: str

    def __init__(self, uuid: str, sock: socket, capacity: int = 4):
        super(Lobby, self).__init__()
        self.capacity = capacity
        self.conns = []
        self.action_queue_inbound = []
        self.action_queue_outbound = []
        self.game_state_lock = Lock()
        self.game_state = GameState(self.game_state_lock, {})
        self.in_game = False
        self.logger = Logger('Lobby')
        self.running = False
        self.uuid = uuid
        self.sock = socket(AF_INET6, SOCK_DGRAM)
        self.logger.info('Lobby init\'d')

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
            # TODO: Handle game state changes
            while not self.is_full:
                # wait until the lobby is full to start the game
                time.sleep(0.03)

            self.in_game = True
            while self.in_game:
                _incoming_changes = []

                with self.game_state_lock:
                    _incoming_changes = self.action_queue_inbound
                    self.action_queue_inbound = []

                # Unpack all incoming changes
                for payload in _incoming_changes:
                    changes = payload.data
                    self.game_state.apply_state(changes)

                time.sleep(0.03)

    def _handle_outgoing(self):
        """
        This method should not be called directly.

        Method running in a separate thread to handle outgoing data.
        The data to be sent is taken from the outbound action queue.
        """
        while self.running:
            # get the queue of actions to be sent

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


# TODO: Implement test suite
