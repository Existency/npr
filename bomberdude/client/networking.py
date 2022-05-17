from __future__ import annotations

from charset_normalizer import from_bytes
from common.location import get_node_xy
from common.state import Change, GameState, change_from_bytes, parse_payload 
from common.payload import ACTIONS, KALIVE, REJOIN, STATE, Payload, ACCEPT, LEAVE, JOIN, REDIRECT, REJECT
from dataclasses import dataclass, field
import logging
import time
from typing import Tuple, List
from threading import Thread, Lock
from socket import socket, AF_INET6, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR, timeout
import json
from common.types import Address


@ dataclass
class NetClient(Thread):
    """
    Networking class used by the client.

    :param remote: The remote address to connect to.
    :param port: The port to connect to.
    """
    auth_ip: Address
    port: int
    #npath: str
    level: int = field(default=logging.INFO)
    slock: Lock = field(init=False, default_factory=Lock)
    gamestate: GameState = field(init=False)
    lobby_uuid: str = field(default='')
    player_uuid: str = field(default='')
    in_sock: socket = field(init=False)
    out_sock: socket = field(init=False)
    inbound_lock: Lock = field(default_factory=Lock)
    queue_inbound: List[Change] = field(
        default_factory=list)
    outbound_lock: Lock = field(default_factory=Lock)
    queue_outbound: List[Tuple[Payload, Address]
                         ] = field(default_factory=list)
    message_lock: Lock = field(default_factory=Lock)
    queue_message: List[Tuple[bytes,
                              Address]] = field(default_factory=list)
    running: bool = field(init=False, default=False)
    player_id: int = field(init=False, default=0)
    started: bool = field(init=False, default=False)
    last_kalive: float = field(init=False, default=0.0)
    lobby_ip: Address = field(init=False)
    start_time: float = field(init=False, default=0.0)
    seq_num: int = field(init=True, default=0)

    # gps related
    cur_pos: Tuple[float, float] = field(init=False, default=(0.0, 0.0))

    def __hash__(self) -> int:
        return super().__hash__()

    def __post_init__(self):
        super(NetClient, self).__init__()
        self.gamestate = GameState(self.slock, {}, {})
        #self.cur_pos = get_node_xy(self.npath)
        logging.basicConfig(
            level=self.level, format='%(levelname)s: %(message)s')

        logging.info('Client init\'d')

    @ property
    def messages(self) -> list:
        """
        Method used to get messages tuples from the queue.
        """
        with self.inbound_lock:
            message: list = self.queue_inbound
            self.queue_inbound = []
            return message

    def join_server(self, lobby_id: str):
        """
        Joins the server, upon joining the ThreadedSocket will start listening.

        :param lobby_id: The lobby ID to join.
        """

        in_sock = socket(AF_INET6, SOCK_DGRAM)
        in_sock.bind(('', self.port))
        in_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        in_sock.settimeout(2)

        out_sock = socket(AF_INET6, SOCK_DGRAM)
        out_sock.bind(('', self.port+1))
        out_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        out_sock.settimeout(2)

        payload = Payload(JOIN, b'', lobby_id, '', self.seq_num)
        retry_payload = Payload(REJOIN, b'', lobby_id, '', self.seq_num)
        retry_bytes = retry_payload.to_bytes()
        self.seq_num = + 1
        in_sock.sendto(payload.to_bytes(), self.auth_ip)

        _try = 0
        _reconnect = 0

        while True:
            try:
                resp, addr = in_sock.recvfrom(1024)

                if len(resp) < 17:
                    # ignore these packets
                    _try -= 1
                    continue

                logging.info("Join: Received response on socket.")

                data = Payload.from_bytes(resp)

                if addr[0] == self.auth_ip[0] and addr[1] == self.auth_ip[1]:
                    if data.type == ACCEPT:
                        self.player_uuid = data.player_uuid
                        self.lobby_uuid = data.lobby_uuid
                        # decode the payload's data.

                        lobby_port = int.from_bytes(
                            data.data, byteorder='big')
                        logging.info('New lobby port: %d', lobby_port)

                        self.lobby_ip = (self.auth_ip[0], lobby_port)
                        self.in_sock = in_sock
                        self.out_sock = out_sock

                        logging.info('Client joined lobby %s', self.lobby_uuid)
                        self.last_kalive = time.time()  # set kalive to now
                        return True

                    elif data.type == REJECT:
                        logging.error('Could not join lobby.')
                        return False
                    else:
                        logging.warning('Server returned invalid action')
                        return False

            except Exception as e:
                logging.error('Exception: %s', e.__str__())

            _try += 1

            if _reconnect > 5:
                # if unable to connect over 10 seconds, give up
                logging.warning('Could not connect to server.')
                return False

            # attempt to reconnect every 2 seconds
            if _try > 8:
                logging.warning('No response from server, reconnecting...')
                _reconnect += 1
                _try = 0
                in_sock.sendto(retry_bytes, self.auth_ip)

            time.sleep(0.25)

    def reset(self):
        """
        Resets the client to its initial state preparing it to join a new lobby.

        Can be used to reset the client after a disconnection.
        """
        self.gamestate.reset()
        self.lobby_uuid = ''
        self.player_uuid = ''
        self.lobby_ip = ('', 0)
        self.player_id = 0
        self.last_kalive = 0.0
        self.running = False
        self.started = False
        self.start_time = 0.0

    # TODO: This will be needed later on
    def multicast(self, data: bytes):
        """
        Method used to broadcast data using an IPv6 multicast address.

        :param data: The data to be broadcasted.
        """
        pass

    def unicast(self, data: bytes):
        """
        Method used to send data to the server.

        :param data: The payload to be sent.
        """
        #print(self.seq_num)
        sent = self.out_sock.sendto(data, self.lobby_ip)
        logging.debug('Sent %d bytes to server', sent)

    def _handle_state(self):
        """
        Method shouldn't be called directly from outside the class.

        This method is used to handle the inbound queue.
        """
        self.started = False
        while self.running:
            while not self.started:
                # Wait until server sends us a STATE message with our ID
                time.sleep(0.1)
                

            # reset for next game
            self.started = False
            self.in_game = True
            while self.in_game:
                _incoming_changes = []

                with self.slock:
                    _incoming_changes = self.queue_inbound
                    #print(f'incoming: {_incoming_changes}')
                    self.queue_inbound = []
                    
                for change in _incoming_changes:
                    self.gamestate._apply_change(change)
                    #print('change',change)
                    #print(self.gamestate.get_player_positions())

                time.sleep(0.03)

    def _broadcast_kalive(self):
        """
        Method shouldn't be called directly from outside the class.

        This method is used to broadcast the kalive to the server.
        """
        while self.running:
            # check whether last kalive from server was more than 5 seconds ago
            if time.time() - self.last_kalive > 5:
                logging.warning('Server not responding...')

            payload = Payload(KALIVE, b'', self.lobby_uuid,
                              self.player_uuid, self.seq_num)
            self.seq_num += 1
            self.unicast(payload.to_bytes())
            time.sleep(1)

    def _handle_output(self):
        """
        Method shouldn't be called directly from outside the class.

        This method is used to handle the outbound queue.
        """
        while self.running:
            actions = []

            with self.outbound_lock:
                actions = self.queue_outbound
                self.queue_outbound = []

            for action in actions:
                self.unicast(action[0].to_bytes())

            time.sleep(0.03)

    def _handle_input(self):
        """
        Method shouldn't be called directly from outside the class.

        Handles the data received from a remote host.
        This data is converted to a Payload object and then handled.
        """
        while self.running:
            try:
                data, addr = self.in_sock.recvfrom(1024)

                if len(data) < 17:
                    continue

                payload = Payload.from_bytes(data)
                
                
                if payload.type == REDIRECT:
                    with self.outbound_lock:
                        self.queue_outbound.append((payload, addr))
                    return

                if payload.lobby_uuid == self.lobby_uuid and payload.player_uuid == self.player_uuid:
                    # Parse the payload and check whether it's an event or not
                    # if it's a game event, add it to the queue_inbound
                    # if it's not, pass it to the queue_message
                    if payload.type == KALIVE:
                       # logging.info('Received KALIVE.')
                        self.last_kalive = time.time()

                    elif payload.type == ACTIONS:
                        
                        changes = change_from_bytes(payload.data)
                        #inc = parse_payload(payload.data)
                        
                        if changes is not None:                               
                            with self.inbound_lock:
                                self.queue_inbound.extend(changes)
                                

                    elif payload.type == STATE and self.started == False:
                        # update the client's state and set the started flag to true

                        state = json.loads(payload.data.decode('utf-8'))
                        if state['uuid'] == self.player_uuid:
                            self.started = True
                            self.start_time = state['time']
                            self.player_id = state['id']
                            #print('dealing with boxes',state['boxes'])
                            self.gamestate.boxes = state['boxes']

            except timeout:
                logging.info('Socket recv timed out.')

            except Exception as e:
                logging.warning('Invalid payload received: %s',
                                e.__str__())

        self.terminate("Unexpected condition leading to termination.")

        pass

    def run(self):
        """
        Main loop of the networking client.
        """
        self.running = True
        Thread(target=self._handle_state).start()
        Thread(target=self._broadcast_kalive).start()
        Thread(target=self._handle_output).start()
        Thread(target=self._handle_input).start()

        while self.running:
            time.sleep(0.1)

    def leave(self):
        """
        Method used to leave the game.
        """
        logging.info('Client leaving lobby by user request.')
        # TODO: Fix seq_num across all files
        payload = Payload(LEAVE, b'', self.lobby_uuid,
                          self.player_uuid, self.seq_num)
        self.seq_num += 1
        self.unicast(payload.to_bytes())
        # terminate the threaded socket

    def terminate(self, reason: str = "Requested by user."):
        """
        Method used to close the client.

        :param reason: The reason for termination.
        """
        logging.info('Networking client terminated: {reason}', reason)
        self.running = False
        self.in_game = False
        self.leave()

# TODO: Implement tests for these.
