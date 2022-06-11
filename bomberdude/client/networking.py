from __future__ import annotations
from common.state import Change, GameState, change_from_bytes, parse_payload
from functools import cached_property
from ipaddress import ip_address
from common.core_utils import get_node_distance, get_node_xy
from common.payload import ACK, KALIVE, REJOIN, Payload, ACCEPT, LEAVE, JOIN, REJECT
from common.cache import Cache
from dataclasses import dataclass, field
import logging
import time
import struct
from typing import Tuple, List
from threading import Thread, Lock
from socket import IPPROTO_UDP, IPV6_JOIN_GROUP, getaddrinfo, socket, AF_INET6, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR, timeout, IPPROTO_IPV6, IPV6_MULTICAST_HOPS, inet_pton
import json
from common.types import DEFAULT_PORT, MCAST_GROUP, MCAST_PORT, Address, MobileMap, MobileMetrics, Position

InboundQueue = List[Change]
"""A list of changes to be applied to the game state."""

OutboundQueue = List[Tuple[Payload, Address]]
"""A list of payloads to be sent."""


@ dataclass
class NetClient(Thread):
    """
    Networking class used by the client.

    :param remote: The remote address to connect to.
    :param port: The port to connect to.
    """

    auth_ip: Address
    """The server's address."""
    node_path: str
    """The node's path in the filesystem."""
    byte_address: bytes
    """The byte representation of the client's address."""
    log_level: int = field(default=logging.INFO)
    """The logging level this client will use."""
    state_lock: Lock = field(init=False, default_factory=Lock)
    """Game state shared lock."""
    gamestate: GameState = field(init=False)
    """The client's game state. This is used to draw the game for the player and to synchronize the game state with others."""
    lobby_uuid: str = field(default='')
    """The lobby's uuid."""
    player_uuid: str = field(default='')
    """The player's uuid."""
    in_sock: socket = field(init=False)
    """The socket used to receive data."""
    out_sock: socket = field(init=False)
    """The socket used to send data."""

    queue_inbound: List[Payload] = field(
        init=False, default_factory=list)

    # cache
    client_cache: Cache = field(init=False)
    """Cache used to store the last sent payloads."""
    cache_timeout: int = field(default=10)
    """The timeout, in seconds, for cache entries to be removed."""
    running: bool = field(init=False, default=False)
    """Whether the client is running."""
    player_id: int = field(init=False, default=0)
    """The player's in-game id. Used to determine it's starting position."""
    start_time: float = field(init=False, default=0.0)
    """Game start time."""
    started: bool = field(init=False, default=False)
    """Whether a game is currently in progress."""
    last_kalive: float = field(init=False, default=0.0)
    """The time of the last KALIVE message."""
    lobby_addr: Address = field(init=False)
    """The lobby's address."""
    seq_num: int = field(init=False, default=0)
    """Sequence number for the client"""

    # This only exists in mobile clients
    mobile_map: MobileMap = field(init=False, default_factory=dict)
    """Information related to other mobile nodes"""
    preferred_mobile: Address = field(init=False)
    """The preferred mobile node to send data to."""
    gateway_addr: Address = field(default=('', 0))
    """The gateway's address. This property is used by mobile nodes only."""
    gateway_map: MobileMap = field(init=False, default_factory=dict)
    """Information about all the gateways in the network."""
    is_mobile: bool = field(default=False)
    """Whether this client is a mobile node."""

    @cached_property
    def msender(self) -> socket:
        """
        The socket through which the gateway node sends messages to the DTN.
        """
        ttl = struct.pack('@I', 3)
        sock = socket(AF_INET6, SOCK_DGRAM)
        sock.setsockopt(IPPROTO_IPV6, IPV6_MULTICAST_HOPS, ttl)
        return sock

    @cached_property
    def dtn_sock(self) -> socket:
        """
        The socket through which the gateway node sends and receives messages from the DTN.
        """
        sock = socket(AF_INET6, SOCK_DGRAM, IPPROTO_UDP)
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        sock.bind(('', MCAST_PORT))
        group = inet_pton(AF_INET6, MCAST_GROUP) + struct.pack('@I', 0)
        sock.setsockopt(IPPROTO_IPV6, IPV6_JOIN_GROUP, group)
        return sock

    def __hash__(self) -> int:
        return super().__hash__()

    def __post_init__(self):
        super(NetClient, self).__init__()
        self.gamestate = GameState(self.state_lock, {}, {})
        self.client_cache = Cache(self.cache_timeout, self.log_level)

        logging.basicConfig(
            level=self.log_level, format='%(levelname)s: %(message)s')

        if self.is_mobile:
            # if gateway_addr is not set, this is an error
            if self.gateway_addr == ('', 0):
                logging.error("Gateway address not set on mobile node.")
                exit(1)
            self.preferred_mobile = self.gateway_addr

            Thread(target=self._handle_dtn_input).start()
            logging.info('DTN input handler started.')
            Thread(target=self._broadcast_kalive_mobile).start()
            logging.info('Kalive (mobile) handler started.')

            while not (self.gateway_map and self.mobile_map):
                # wait for at least one gateway and one mobile node to join
                time.sleep(0.1)

            logging.info('Gateway and Mobile Map init\'d.', self.gateway_map)

        logging.info('Client init\'d.')

    @property
    def location(self) -> Position:
        """
        Method used to get the current location of the client.
        """
        return get_node_xy(self.node_path)

    @property
    def closest_gateway(self) -> Tuple[Address, MobileMetrics]:
        """
        Returns the closest gateway to the client from the gateway map.
        """
        # recalculate and update each gateway's distance to the client
        for (addr, metrics) in self.gateway_map.items():
            self.gateway_map[addr] = self.gateway_update(metrics)

        closest = min(self.gateway_map.items(), key=lambda x: x[1][0])

        return (closest[0], closest[1])

    @cached_property
    def lobby_byte_address(self) -> bytes:
        """
        Returns the byte address of the lobby.
        """
        # use inet_pton
        return inet_pton(AF_INET6, self.lobby_addr[0])

    def gateway_update(self, metrics: MobileMetrics) -> MobileMetrics:
        """
        Updates the gateway's distance to the client.
        """
        (_, pos, time, hops) = metrics
        dist = get_node_distance(self.location, pos)
        return (dist, pos, time, hops)

    def join_server(self, lobby_id: str):
        """
        Joins the server, upon joining the ThreadedSocket will start listening.

        :param lobby_id: The lobby ID to join.
        """
        in_sock = socket(AF_INET6, SOCK_DGRAM)
        in_sock.bind(('', DEFAULT_PORT))
        in_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        in_sock.settimeout(2)

        out_sock = socket(AF_INET6, SOCK_DGRAM)
        out_sock.bind(('', DEFAULT_PORT+1))
        out_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        out_sock.settimeout(2)

        print(self.byte_address)

        payload = Payload(JOIN, b'', lobby_id, '',
                          self.seq_num, self.byte_address, self.byte_address, DEFAULT_PORT)

        retry_payload = Payload(REJOIN, b'', lobby_id,
                                '', self.seq_num, self.byte_address, self.byte_address, DEFAULT_PORT)
        retry_bytes = retry_payload.to_bytes()
        self.seq_num = + 1
        print("address: ", self.auth_ip)
        in_sock.sendto(payload.to_bytes(), self.auth_ip)

        _try = 0
        _reconnect = 0

        while True:
            try:
                resp, addr = in_sock.recvfrom(1500)

                if len(resp) < 50:
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

                        self.lobby_addr = (self.auth_ip[0], lobby_port)
                        self.in_sock = in_sock
                        self.out_sock = out_sock

                        logging.info('Client joined lobby %s', self.lobby_uuid)
                        self.last_kalive = time.time()  # set kalive to now
                        self.running = True
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
        self.lobby_addr = ('', 0)
        self.player_id = 0
        self.last_kalive = 0.0
        self.running = False
        self.started = False
        self.start_time = 0.0

    @cached_property
    def mcast_addr(self) -> Address:
        """
        Returns the multicast address of the lobby.
        """
        return (getaddrinfo(MCAST_GROUP, None)[0][4][0], MCAST_PORT)

    def unicast(self, data: bytes):
        """
        Method used to send data to the server.

        :param data: The payload to be sent.
        """
        sent = self.out_sock.sendto(data, self.lobby_addr)
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

                with self.state_lock:
                    _incoming_changes = self.queue_inbound
                    self.queue_inbound = []
                for change in _incoming_changes:
                    self.gamestate._apply_change(change)
                    # print('change',change)
                    # print(self.gamestate.get_player_positions())

                time.sleep(0.03)

    def _broadcast_kalive_mobile(self):
        """
        Method shouldn't be called directly from outside the class.


        This message is used to broadcast the kalive to the server in a mobile context.
        """
        byte_address = inet_pton(AF_INET6, MCAST_GROUP)

        while True:
            # check whether last kalive from server was more than 5 seconds ago
            #if time.time() - self.last_kalive > 5:
            #    logging.warning('Server not responding...')

            location = self.location

            data = bytes(str(location[0]) +
                         ',' + str(location[1]), 'utf-8')

            if self.running:
                payload = Payload(KALIVE, data, self.lobby_uuid, self.player_uuid, self.seq_num,
                                self.byte_address, byte_address, self.lobby_addr[1])
            else:
                payload = Payload(KALIVE, data, '', '', self.seq_num,
                                    self.byte_address, byte_address, MCAST_PORT)

            self.msender.sendto(payload.to_bytes(), self.mcast_addr)
            print("Sending Kalive to ",self.mcast_addr)
            time.sleep(0.5)

    def _broadcast_kalive_wired(self):
        """
        Method shouldn't be called directly from outside the class.

        This method is used to broadcast the kalive to the server.
        """

        location = self.location
        data = bytes(str(location[0]) +
                     ',' + str(location[1]), 'utf-8')

        # non mobile clients
        while self.running:
            # check whether last kalive from server was more than 5 seconds ago
            if time.time() - self.last_kalive > 5:
                logging.warning('Server not responding...')

            payload = Payload(KALIVE, data, self.lobby_uuid,
                              self.player_uuid, self.seq_num, self.byte_address, self.lobby_byte_address,self.lobby_addr[1])

            self.seq_num += 1
            self.unicast(payload.to_bytes())
            time.sleep(1)

    def _handle_metrics_update(self):
        """
        Method shouldn't be called directly from outside the class.

        This method is used to automatically update the prefered destination node.
        """
        while self.running:
            time.sleep(1)
            # Every 5 seconds update the preffered mobile node and set it's address as the default.
            self.preferred_mobile = self._get_preferred_node()
            logging.info('Preferred mobile node is {}'.format(
                self.preferred_mobile[0]))

    def _get_preferred_node(self) -> Address:
        """
        Returns a node.

        :return: The node with the lowest distance to the gateway node aswell as a low number of hops.
        """
        # get the closest gateway to our node
        (gateway_addr, (dist, _, _, hops)) = self.closest_gateway

        # get the gateway node
        # (dist, _, _, hops) = self.mobile_map[self.gateway_addr]

        # Important: if we're connected directly to the gateway,
        #               we want to use it as a preferred node.
        if hops == 3:
            return gateway_addr

        distances = [self.mobile_map[addr][0] for addr in self.mobile_map]

        # get the shortest distance
        min_dist = min(distances)

        candidates = [
            addr for addr in self.mobile_map if self.mobile_map[addr][0] == min_dist]

        best_candidate = min(candidates, key=lambda x: self.mobile_map[x][0])
            
        # if the min_dist is no less than 20% larger than the gateway node and has less hops, return the gateway node
        if min_dist * 1.1 > dist and self.mobile_map[best_candidate][3] >= hops:
            return best_candidate

        return gateway_addr

    def _handle_output_mobile(self):
        """
        Method shouldn't be called directly from outside the class.

        This method is used to handle the output queue in a mobile context.
        """
        while self.running:
            payloads = self.client_cache.get_entries_not_sent()

            # get prefered destination node
            out_addr = (self.preferred_mobile[0],DEFAULT_PORT )
        
            
            for (addr, payload) in payloads:
                logging.info(
                    'Sending payload to {} through {}.'.format(addr, out_addr))
                payload.port = self.lobby_addr[1]
                self.out_sock.sendto(payload.to_bytes(), out_addr)

            time.sleep(0.1)

    def _handle_output_wired(self):
        """
        Method shouldn't be called directly from outside the class.

        This method is used to handle the outbound queue.
        """
        while self.running:
            payloads = self.client_cache.get_entries_not_sent()

            for (addr, payload) in payloads:
                logging.debug(
                    'Sending payload to {}.'.format(addr))
                self.unicast(payload.to_bytes())

            time.sleep(0.03)

    def _handle_dtn_input(self):
        """
        Method shouldn't be called directly from outside the class.

        Handles the data received from the DTN network.
        """

        while True:
            try:
                data, addr = self.dtn_sock.recvfrom(1500)

                address = (addr[0], addr[1])
                payload = Payload.from_bytes(data)

                #print(payload.type)

                if payload is None:
                    logging.warning(
                        'Received invalid payload from {}.'.format(address))
                    continue

                if payload.is_gkalive:
                    _x, _y = payload.data.decode('utf-8').split(',')
                    position = (float(_x), float(_y))
                    hops = 3 - payload.ttl
                    timestamp = time.time()
                    distance = get_node_distance(position, self.location)

                    self.gateway_map[address] = (
                        distance, position, timestamp, hops)

                    self.mobile_map[address] = (
                        distance, position, timestamp, hops)

                if payload.is_kalive:
                    _x, _y = payload.data.decode('utf-8').split(',')
                    position = (float(_x), float(_y))
                    hops = 3 - payload.ttl
                    timestamp = time.time()
                    distance = get_node_distance(position, self.location)

                    self.mobile_map[address] = (
                        distance, position, timestamp, hops)

            except timeout:
                continue
            except Exception as e:
                logging.error(e)
                continue

    def _handle_input(self):
        """
        Method shouldn't be called directly from outside the class.

        Handles the data received from a remote host.
        """
        while self.running:
            try:
                data, _ = self.in_sock.recvfrom(1500)

                if len(data) < 50:
                    continue

                payload = Payload.from_bytes(data)

                if payload.is_redirect:
                    self.client_cache.add_entry(
                        (payload.short_destination, DEFAULT_PORT), payload)

                if payload.lobby_uuid == self.lobby_uuid and payload.player_uuid == self.player_uuid:
                    # Parse the payload and check whether it's an event or not
                    # if it's a game event, add it to the queue_inbound
                    # if it's not, pass it to the queue_message
                    if payload.is_kalive:
                        self.last_kalive = time.time()

                    elif payload.is_actions:
                        changes = change_from_bytes(payload.data)

                        if changes is not None:
                            self.queue_inbound.extend(changes)

                        # Ack the payload
                        ack_payload = Payload(ACK, b'', self.lobby_uuid, self.player_uuid,
                                              payload.seq_num, self.byte_address, self.lobby_byte_address, self.lobby_addr[1])

                        self.client_cache.add_entry(
                            (payload.short_source, DEFAULT_PORT), ack_payload)

                    elif payload.is_state and self.started == False:
                        # update the client's state and set the started flag to true
                        state = json.loads(payload.data.decode('utf-8'))
                        if state['uuid'] == self.player_uuid:
                            self.started = True
                            self.start_time = state['time']
                            self.player_id = state['id']
                            # print('dealing with boxes',state['boxes'])
                            self.gamestate.boxes = state['boxes']

            except timeout:
                continue
            except Exception as e:
                logging.warning('Invalid payload received: %s',
                                e.__str__())

        self.terminate("Unexpected condition leading to termination.")

    def run(self):
        """
        Main loop of the networking client.
        """
        Thread(target=self._handle_state).start()
        logging.info('State handler started.')
        Thread(target=self._handle_input).start()
        logging.info('Input handler started.')

        if self.is_mobile:
            Thread(target=self._handle_output_mobile).start()
            logging.info('Output (mobile) handler started.')
            Thread(target=self._handle_metrics_update).start()
            logging.info('Metrics update handler started.')
        else:
            Thread(target=self._broadcast_kalive_wired).start()
            logging.info('Kalive (wired) handler started.')
            Thread(target=self._handle_output_wired).start()
            logging.info('Output (wired) handler started.')

        # main loop, if we're mobile purge cache every X seconds
        if self.is_mobile:
            while self.running:
                time.sleep(self.cache_timeout)
                self.client_cache.purge_timeout()
        else:
            while self.running:
                time.sleep(1)

    def leave(self):
        """
        Method used to leave the game.
        """
        logging.info('Client leaving lobby by user request.')
        # TODO: Fix seq_num across all files
        payload = Payload(LEAVE, b'', self.lobby_uuid,
                          self.player_uuid, self.seq_num, self.byte_address, b'', self.lobby_addr[1])

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
