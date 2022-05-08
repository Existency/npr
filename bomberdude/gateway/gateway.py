"""
Edge nodes for the DTN network.

These nodes are used by the DTN network to send and receive messages.
The mobile nodes will use the edge nodes to send and receive messages.
"""
from functools import cached_property
import logging
from socket import socket, AF_INET6, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR, SO_REUSEPORT
import time

from dataclasses import dataclass, field
from threading import Thread, Lock
from typing import Dict, List, Tuple

from common.payload import ACK, KALIVE, Payload
from common.types import Distance, Hops, Position, Address, Time
from common.cache import Cache
from common.location import get_node_distance, get_node_xy


MobileData = Tuple[Distance, Position, Time, Hops]
"""
    Distance: The distance between the mobile node and the edge node.
    Position: The (x, y) coordinates of the edge node.
    Time: The time when the mobile node last sent a message.
    Hops: The number of hops the mobile node's data has made.
"""

MobileMap = Dict[Address, MobileData]
"""
    Address: The node's address.
    MobileData: The node's data.
"""


@dataclass
class EdgeNode:
    """
    Edge node for the DTN network.
    """
    server_address: Address
    """The server's address"""

    node_path: str
    """The node's system path (CORE related)."""

    port: int = field(default=9191)
    """The port to listen on."""

    cache_timeout: int = field(default=20)
    """Cache timeout in seconds."""

    level: int = field(default=logging.INFO)
    """The logging level."""

    in_socket: socket = field(init=False)
    """Socket through which the edge node receives messages from the network."""

    out_socket: socket = field(init=False)
    """Socket through which the edge node sends messages to the network."""

    running: bool = field(default=False, init=False)
    """Whether the node is running."""

    position: Position = field(init=False)
    """The (x, y) coordinates of this node."""

    mobile_nodes: MobileMap = field(init=False, default_factory=dict)
    """A list of mobile nodes and some data about them."""

    outgoing_mobile: Cache = field(init=False)
    """Messages meant for mobile nodes."""

    outgoing_srv_lock: Lock = field(init=False, default_factory=Lock)
    """Lock for the outgoing server list."""

    outgoing_server: List[Payload] = field(default_factory=list, init=False)
    """Messages meant for the server."""

    # TODO: Use ttl aswell as the gps coordinates as a metric to determine whether a node is stale.

    #       Modify the way broadcasts are made in the mobile nodes (networking.py).
    #       Include the gps coordinates in the KALIVE message.
    #       Edge will remove gps coordinates from KALIVE messages before sending to server.

    def __post_init__(self):
        logging.basicConfig(
            level=self.level, format='%(levelname)s: %(message)s')

        self.position = get_node_xy(self.node_path)

        # Create the sockets, both on the same port
        in_sock = socket(AF_INET6, SOCK_DGRAM)
        in_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        in_sock.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1)
        in_sock.bind(('', self.port))
        in_sock.settimeout(2)
        self.in_socket = in_sock

        out_sock = socket(AF_INET6, SOCK_DGRAM)
        out_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        out_sock.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1)
        out_sock.bind(('', self.port))
        out_sock.settimeout(2)
        self.in_socket = out_sock

        # Create the outgoing cache
        self.outgoing_mobile = Cache(self.cache_timeout, level=self.level)

        logging.info('Edge node initialized on {}'.format(self.position))

    def __hash__(self) -> int:
        return super().__hash__()

    @cached_property
    def kalive(self) -> bytes:
        """
        The data to be sent on KALIVE messages.
        Cached since gateway nodes won't ever change their position.

        :return: The data to be send in the KALIVE messages.
        """
        data = bytes(str(self.position[0]) +
                     ',' + str(self.position[1]), 'utf-8')

        payload = Payload(KALIVE, data, "", "", 0)

        return payload.to_bytes()

    def _broadcast_kalive(self):
        """
        KALIVE message broadcast.

        This message is used to inform mobile nodes that the edge node is still alive.
        TODO: Mobile nodes will use this message to determine the amount of jumps that have been made.
        """
        while self.running:
            logging.info('Broadcasting KALIVE')
            # TODO: Requires all mobiles nodes to use the same port? Check this.
            self.out_socket.sendto(self.kalive, ('ff02::1', self.port))
            time.sleep(1)

    def handle_kalive(self, addr: Address, payload: Payload) -> Payload:
        """
        Handles KALIVE messages.
        """
        try:
            # check whether the node is already in the list
            if addr in self.mobile_nodes:
                timestamp = time.time()
                hops = 3 - payload.ttl
                # payload's data to str
                _x, _y = payload.data.decode('utf-8').split(',')
                position = (float(_x), float(_y))
                # get distance between the node and the edge node
                distance = get_node_distance(position, self.position)
                # update the node's data
                self.mobile_nodes[addr] = (distance, position, timestamp, hops)
        except Exception as e:
            logging.error('Failed to handle KALIVE message: {}'.format(e))

        # null the payload's data
        payload.data = b''

        return payload

    def _handle_incoming(self):
        """
        Handles the incoming messages.

        If messages are received from mobile nodes they are inserted into the outgoing_server cache.

        If messages are received from the server they are stored in mobile_cache and sent to the mobile nodes.
            - If the message is an Ack, remove this message from the mobile_cache.
            - If a message hasn't been Ack'd in N seconds, discard it as it's destinatary likely been disconnected.
        """
        while self.running:
            try:
                data, addr = self.in_socket.recvfrom(1024)

                address = (addr[0], addr[1])

                payload = Payload.from_bytes(data)

                # Figure whether the message is from the server or from a mobile node
                if address == self.server_address:
                    self.outgoing_mobile.add_entry(payload)
                    logging.info('Received message from server.')
                else:
                    if payload.type == KALIVE:
                        payload = self.handle_kalive(address, payload)

                    # TODO: Implement the following:
                    #       - If the message is an ACK, remove it from the mobile_cache.
                    #       - Refactor the payload class to include the TTL, Sender and Receiver addresses.

                    # if payload.type == ACK:
                    #     self.outgoing_mobile.purge_entries(
                    #         payload.seq_num, payload.address)

                    with self.outgoing_srv_lock:
                        self.outgoing_server.append(payload)
                    logging.info('Received message from mobile node.')

            except Exception as e:
                logging.error(e)
                continue

    def _handle_outgoing(self):
        """
        Handles the outgoing messages.
        """

        while self.running:
            # Send messages to the server
            outgoing = []
            with self.outgoing_srv_lock:
                outgoing = self.outgoing_server
                self.outgoing_server = []

            for payload in outgoing:
                self.out_socket.sendto(payload.to_bytes(), self.server_address)
                logging.info('Sent message to server.')

            # Send messages to the mobile nodes
            for entry in self.outgoing_mobile.get_entries():
                # TODO: Requires three changes that I can think of right now.
                #       1. The payload will need to be changed to include TTL aswell as Sender/Receiver Addresses.
                #       2. The mobile nodes will need a local cache of nearby nodes, this way they can send messages to their neighbors.
                #       3. The same ACK system as on gateway.py#192 should be implemented on mobile nodes.

                self.out_socket.sendto(entry[1].to_bytes(), entry[0])

    def _handle_cache_timeout(self):
        """
        Every N seconds the cache is checked for messages that timed out.

        If a message has timed out, it is removed from the cache.
        """
        while self.running:
            self.outgoing_mobile.purge_entries()
            time.sleep(self.cache_timeout)

    def run(self):
        """
        Main loop of the Edge Node.
        """
        self.running = True
        Thread(target=self._broadcast_kalive).start()
        logging.info('Broadcast KALIVE thread started')
        Thread(target=self._handle_incoming).start()
        logging.info('Handle incoming thread started')
        Thread(target=self._handle_outgoing).start()
        logging.info('Handle outgoing thread started')
        Thread(target=self._handle_cache_timeout).start()

        # Keep the main thread alive
        while self.running:
            time.sleep(1)

    def leave(self):
        """
        Attempt to send all messages to the network.

        Afterwards, the node will closed.
        """

        # TODO: Send all messages to the network
        logging.info('Leaving edge node')

    def terminate(self, reason: str = "Unknown"):
        """
        Method used to close the edge node.

        :param reason: The reason for closing the node.
        """

        logging.info('Terminating edge node: {}'.format(reason))
        self.running = False
        self.leave()
