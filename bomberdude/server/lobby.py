from __future__ import annotations
from .connection import Conn
from common.state import GameState
from common.payload import ACTIONS, KALIVE, LEAVE, STATE, Payload
from common.state import Change, bytes_from_changes, change_from_bytes
from dataclasses import dataclass, field
from functools import singledispatchmethod
import logging
from socket import socket, timeout
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
    in_sock: socket
    out_sock: socket
    # logging level
    byte_address: bytes
    level: int = field(default=logging.DEBUG)
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
    # flag to indicate whether the lobby is running
    running: bool = field(init=False, default=False)

    def __hash__(self) -> int:
        return super().__hash__()

    def __post_init__(self):
        """
        This method should not be called directly.

        Method that is called after the lobby has been initialized.
        """
        super(Lobby, self).__init__()
        self.game_state_lock = Lock()
        self.game_state = GameState(self.game_state_lock, {}, {})
        logging.basicConfig(
            level=self.level, format='%(levelname)s: %(message)s')

        logging.info('Lobby post init\'d')

    def add_player(self, conn: Conn) -> bool:
        """
        Adds a conn to the lobby.

        :param conn: The conn to be added.
        """
        if self.is_full:
            logging.info(
                'Lobby is fully, cannot add conn, %s', conn.__str__())
            return False

        # check whether the connection already exists
        for c in self.conns:
            if c.address == conn.address:
                logging.info(
                    'Connection already exists, %s', conn.__str__())
                return False

        self.conns.append(conn)
        logging.info('Added conn to lobby, %s', conn.__str__())
        return True

    @singledispatchmethod
    def get_player(self, addr: Tuple[str, int]) -> Optional[Conn]:
        """
        Gets a conn from the lobby.

        :param addr: The address of the conn to be retrieved.
        """
        for c in self.conns:
            if c.address == addr:
                return c
        return None

    @get_player.register
    def _(self, uuid: str) -> Optional[Conn]:
        """
        Gets a conn from the lobby.

        :param addr: The uuid of the conn to be retrieved.
        """
        for c in self.conns:
            if c.uuid == uuid:
                return c
        return None

    def remove_player(self, conn) -> bool:
        """
        Removes a conn from the lobby.

        :param conn: The conn to be removed.
        """
        if conn not in self.conns:
            logging.info(
                'Connection not found, %s', conn.__str__())
            return False

        self.conns.remove(conn)
        logging.info('Removed conn from lobby, %s', conn.__str__())
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
        return self.in_sock.getsockname()

    @property
    def ip(self) -> str:
        """
        Fetches the ip address of the lobby.
        """
        return self.in_sock.getsockname()[0]

    @property
    def port(self) -> int:
        """
        Fetches the port of the lobby.
        """
        return self.in_sock.getsockname()[1]

    # TODO: Find out how ipv6 will affect this
    def unicast(self, data: bytes, conn: Conn):
        """
        Sends data to a conn in the lobby.

        :param data: The data to be sent.
        :param conn: The conn to be sent to.
        """
        if conn not in self.conns:
            raise ValueError('Connection not found')

        conn.send(data, self.out_sock)

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
            c.send(data, self.out_sock)

    def _handle_incoming_data(self):
        """
        This method should not be called directly.

        Method that will run in a separate thread to handle incoming data.
        """
        while self.running:

            try:
                data, _ = self.in_sock.recvfrom(1500)

                # parse the data
                payload = Payload.from_bytes(data)
                logging.info('Received payload, %s', payload.type_str)
                # get the conn that sent the data
                conn = self.get_player(payload.player_uuid)

                if conn is None:
                    # TODO: Change this later for NDN redirect support
                    logging.debug('Connection not found.',)
                    continue

                # If the payload's sequence number is equal or older than the current one, discard
                # TODO: This is a hack fix, will require some work later on
                if payload.seq_num <= conn.seq_num:
                    print('Sequence number is older, %s', conn.__str__())
                    logging.debug('Sequence number is older, %s',
                                  conn.__str__())
                    continue
                conn.seq_num += 1

                # If it's an action, append it to the action queue
                if payload.type == ACTIONS:
                    with self.game_state_lock:
                        self.action_queue_inbound.append(payload)
                    #print('Appended action to action queue, %s', conn.__str__())
                    #logging.debug('Appended action to action queue, %s', conn.__str__())

                elif payload.type == LEAVE:
                    try:
                        self.remove_player(conn)
                    except ValueError:
                        logging.error(
                            'Attempt to remove unexistent connection, %s', conn.__str__())

                elif payload.type == KALIVE:
                    #logging.info('Received KALIVE, %s', conn.__str__())
                    conn.kalive()

                else:
                    # Unhandled payload type
                    logging.error(
                        'Unhandled payload type, %d', payload.type)

            except timeout:
                logging.debug('Socket timeout on _handle_incoming_data')

            except Exception as e:
                logging.error(
                    'Error in _handle_incoming_data, %s', e.__str__())
            time.sleep(0.01)

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
            _out: Dict[Conn, Dict[str, int | float |
                                  str | Dict[int, Tuple[int, int]]]] = {}
            start_time = time.time()

            self.game_state.generate_map()

            print('sending boxes: ', self.game_state.boxes)

            for i, c in enumerate(self.conns):
                _out[c] = {
                    'id': i+1,
                    'time': start_time,
                    'uuid': c.uuid,
                    'boxes': self.game_state.boxes
                }

            while start_time + 5 > time.time():
                for k, v in _out.items():
                    data = json.dumps(v).encode()
                    payload = Payload(STATE, data, self.uuid,
                                      k.uuid, 0, self.byte_address, k.byte_address)
                    k.send(payload.to_bytes(), self.out_sock)
                time.sleep(0.05)

            logging.info('Game started on lobby %s', self.uuid)

            while self.in_game:
                _incoming_changes = []

                with self.game_state_lock:
                    _incoming_changes = self.action_queue_inbound
                    self.action_queue_inbound = []

                # Unpack all incoming changes
                for payload in _incoming_changes:
                    changes = change_from_bytes(payload.data)
                    #changes = payload.data
                    for change in changes:
                        self.game_state._apply_change(change)
                    print(changes)
                    # append updates to the outgoing queue
                    self.action_queue_outbound.extend(changes)

                time.sleep(0.03)

            # Game over
            logging.info('Game over on lobby %s', self.uuid)
            self.game_state.reset()

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
                payload = Payload(ACTIONS, data, self.uuid,
                                  c.uuid, 0, self.byte_address, c.byte_address)

                c.send(payload.to_bytes(), self.out_sock)

            time.sleep(0.001)

    def _kalive_and_timeout(self):
        """
        This method should not be called directly from outside the lobby.

        Method running in a separate thread to broadcast kalives to all conns and handle timeouts.
        """
        # every 1 second send a kalive to all conns
        while self.running:
            time.sleep(1)

            for c in self.conns:
                if c.timed_out:
                    self.remove_player(c)

            # if no one is connected, stop the lobby
            if len(self.conns) == 0:
                self.terminate()

            sent = 0

            for c in self.conns:
                sent += c.send(Payload(KALIVE, b'', self.uuid,
                                       c.uuid, 0, self.byte_address, c.byte_address).to_bytes(), self.out_sock)

            logging.debug('Sent %d bytes', sent)

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

        logging.info('Lobby started')

        # Spawn threads
        Thread(target=self._handle_game_state_changes).start()
        Thread(target=self._handle_incoming_data).start()
        Thread(target=self._handle_outgoing).start()
        Thread(target=self._kalive_and_timeout).start()

        while self.running:
            time.sleep(0.1)

    def terminate(self):
        """
        Terminates the lobby.
        """
        logging.info('Terminating lobby')
        self.running = False
        self.in_game = False


# TODO: Implement test suite
