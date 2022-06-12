from __future__ import annotations
from ipaddress import ip_address

from common.types import DEFAULT_PORT, TIMEOUT, Address
from .connection import Conn
from common.state import GameState
from common.payload import ACK, ACTIONS, KALIVE, STATE, Payload
from common.state import Change, bytes_from_changes, change_from_bytes
from common.cache import Cache
from dataclasses import dataclass, field
import logging
from socket import AF_INET6, inet_pton, socket, timeout
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

    # Cache related class properties
    cache_timeout: int = field(default=30)
    """Default amount of time to wait for a message to be ACKed."""

    outbound: Cache = field(init=False)
    """Cache of outbound payloads."""

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
        self.outbound = Cache(self.cache_timeout, level=self.level)

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

    def get_player(self, addr: Tuple[str, int]) -> Optional[Conn]:
        """
        Gets a conn from the lobby.

        :param addr: The address of the conn to be retrieved.
        """
        for c in self.conns:
            if c.address == addr:
                return c
        return None

    def get_player_by_uuid(self, uuid: str) -> Optional[Conn]:
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
                data, addr = self.in_sock.recvfrom(1500)

                # parse the data
                payload = Payload.from_bytes(data)
                logging.debug('Received payload, %s %s', payload.type_str, payload.short_source)
                # get the conn that sent the data
                conn = self.get_player_by_uuid(payload.player_uuid)

                if conn is None:
                    # TODO: Change this later for NDN redirect support
                    logging.info('Connection not found.',)
                    continue
                
                addr_aux = (addr[0],DEFAULT_PORT)
                
                if conn.address != addr_aux:
                    print("addresses ",addr_aux, conn.address,payload.short_source)
                    conn.address = addr_aux
                    
                #    conn.byte_address = inet_pton(AF_INET6, ip_address(addr_aux[0]).exploded )
                
                # handle ACKs as these might have an invalid seq_num
                if payload.is_ack:
                    self.outbound.purge_entry(
                        (payload.short_source, DEFAULT_PORT), payload)
                    continue

                    # If the payload's sequence number is equal or older than the current one, discard
                    # TODO: This is a hack fix, will require some work later on.
                if payload.seq_num <= conn.seq_num:
                    #print('Sequence number is older, %s', conn.__str__())
                    logging.debug('Sequence number is older, %s',
                                  conn.__str__())
                 #   continue
                conn.seq_num += 1

                # If it's an action, append it to the action queue
                if payload.is_actions:
                    with self.game_state_lock:
                        self.action_queue_inbound.append(payload)
                        ack_payload = Payload(
                            ACK, b'', self.uuid, conn.uuid, payload.seq_num, self.byte_address, payload.source, DEFAULT_PORT)
                        self.outbound.add_entry(
                            (payload.short_source, DEFAULT_PORT), ack_payload)

                elif payload.is_leave:
                    try:
                        self.remove_player(conn)
                        # acknowledge the leave
                        ack_payload = Payload(
                            ACK, b'', self.uuid, conn.uuid, payload.seq_num, self.byte_address, payload.source, DEFAULT_PORT)
                        self.outbound.add_entry(
                            (payload.short_source, DEFAULT_PORT), ack_payload)

                    except ValueError:
                        logging.error(
                            'Attempt to remove unexistent connection, %s', conn.__str__())

                elif payload.is_kalive:
                    logging.debug('Received KALIVE, %s', conn.__str__())
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
            _out = {}
            # _out: Dict[Conn, Dict[str, int | float |
            #                      str | Dict[int, Tuple[int, int]]]] = {}
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

            while start_time + 2 > time.time():
                for k, v in _out.items():
                    data = json.dumps(v).encode()
                    payload = Payload(STATE, data, self.uuid,
                                      k.uuid, 0, self.byte_address, k.byte_address, DEFAULT_PORT)
                    k.send(payload.to_bytes(), self.out_sock)
                time.sleep(0.05)

            logging.info('Game started on lobby %s', self.uuid)

            while self.in_game:
                _incoming_changes = []

                with self.game_state_lock:
                    _incoming_changes = self.action_queue_inbound
                    self.action_queue_inbound = []

                for c in self.conns:
                    if c.timed_out:
                        self.remove_player(c)
                        id = _out[c]['id']
                        lobby_uuid = _out[c]['uuid']
                        data = Change((0, 0, id+9), (0, 0, id + 109))
                        print('killed player', id)
                        payload = Payload(ACTIONS, data.to_bytes(
                        ), lobby_uuid, id, 0, self.byte_address, c.byte_address, DEFAULT_PORT)
                        _incoming_changes.append(payload)

                # Unpack all incoming changes
                for payload in _incoming_changes:
                    changes = change_from_bytes(payload.data)
                    # changes = payload.data
                    for change in changes:
                        self.game_state._apply_change(change)
                    #print(changes)
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
        _last_cleanup = time.time()

        while self.running:
            if len(self.action_queue_outbound) != 0:

                actions = []
                with self.game_state_lock:
                    actions = self.action_queue_outbound
                    self.action_queue_outbound = []

                # convert actions to bytes
                data = bytes_from_changes(actions)

                for c in self.conns:
                    # TODO: add this to cache's sent payloads
                    payload = Payload(ACTIONS, data, self.uuid,
                                      c.uuid, c.seq_num, self.byte_address, c.byte_address, DEFAULT_PORT)

                    # cache the payload
                    self.outbound.add_sent_entry(c.address, payload)
                    c.send(payload.to_bytes(), self.out_sock)

                # get payloads from the outbound cache
                payloads = self.outbound.get_entries_not_sent()

                #if time.time() - _last_cleanup > self.cache_timeout:
                #    payloads = payloads + self.outbound.purge_timeout()
                #    _last_cleanup = time.time()
                    
                # sort the payloads by connection
                payloads_by_conn: Dict[Address, List[Payload]] = {}
                for (addr, payload) in payloads:
                    if addr not in payloads_by_conn:
                        payloads_by_conn[addr] = []
                    payloads_by_conn[addr].append(payload)

                for c in self.conns:
                    if c.address in payloads_by_conn:
                        for payload in payloads_by_conn[c.address]:
                            c.send(payload.to_bytes(), self.out_sock)

                time.sleep(0.03)

    def _kalive(self):
        """
        This method should not be called directly from outside the lobby.

        Method running in a separate thread to broadcast kalives to all conns and handle timeouts.
        """
        # every 1 second send a kalive to all conns
        while self.running:
            time.sleep(1)

            # if no one is connected, stop the lobby
            if len(self.conns) == 0:
                self.terminate()

            sent = 0

            for c in self.conns:
                sent += c.send(Payload(KALIVE, b'', self.uuid,
                                       c.uuid, 0, self.byte_address, c.byte_address, DEFAULT_PORT).to_bytes(), self.out_sock)

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
        Thread(target=self._kalive).start()

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
