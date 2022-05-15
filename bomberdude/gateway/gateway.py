"""
gateway nodes for the DTN network.

These nodes are used by the DTN network to send and receive messages.
The mobile nodes will use the gateway nodes to send and receive messages.
"""
from ipaddress import ip_address
import logging
import time
import struct

from dataclasses import dataclass, field
from functools import cached_property
from socket import IPPROTO_IPV6, IPPROTO_UDP, IPV6_JOIN_GROUP, IPV6_MULTICAST_HOPS, getaddrinfo, socket, AF_INET6, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR, SO_REUSEPORT, inet_pton, getaddrinfo
from threading import Thread, Lock
from typing import List, Optional

from common.payload import ACK, KALIVE, Payload
from common.types import MCAST_GROUP, MCAST_PORT, Position, Address, MobileMap
from common.cache import Cache
from common.core_utils import get_node_distance, get_node_xy


@dataclass
class EdgeNode:
    """
    gateway node for the DTN network.
    """
    server_address: Address
    """The server's address"""

    node_path: str
    """The node's system path (CORE related)."""

    gateway_dtn_address: str
    """The address used to interact with the DTN"""

    port: int = field(default=9191)
    """The port to listen on."""

    cache_timeout: int = field(default=20)
    """Cache timeout in seconds."""

    level: int = field(default=logging.INFO)
    """The logging level."""

    running: bool = field(default=False, init=False)
    """Whether the node is running."""

    mobile_nodes: MobileMap = field(init=False, default_factory=dict)
    """A list of mobile nodes and some data about them."""

    outgoing_mobile: Cache = field(init=False)
    """Messages meant for mobile nodes."""

    outgoing_srv_lock: Lock = field(init=False, default_factory=Lock)
    """Lock for the outgoing server list."""

    outgoing_server: List[Payload] = field(default_factory=list, init=False)
    """Messages meant for the server."""

    # TODO: Use ttl aswell as the coordinates as a metric to determine whether a node is stale.

    #       Modify the way broadcasts are made in the mobile nodes (networking.py).
    #       Include the  coordinates in the KALIVE message.
    #       Edge will remove coordinates from KALIVE messages before sending to server.

    def __hash__(self) -> int:
        return super().__hash__()

    def __post_init__(self):
        logging.basicConfig(
            level=self.level, format='%(levelname)s: %(message)s')

        # Create the outgoing cache
        self.outgoing_mobile = Cache(self.cache_timeout, level=self.level)

        logging.info('gateway node initialized on {}'.format(self.position))

    @cached_property
    def position(self) -> Position:
        """
        The (x, y) coordinates of this node.

        The gateway's position doesn't change so this property is cached.
        """
        return get_node_xy(self.node_path)

    @cached_property
    def kalive(self) -> bytes:
        """
        The data to be sent on KALIVE messages.
        Cached since gateway nodes won't ever change their position.

        :return: The data to be send in the KALIVE messages.
        """
        ip = self.gateway_dtn_address
        ip_src = struct.pack('!8H', *[int(part, 10)
                             for part in ip.split(':')])

        data = bytes(str(self.position[0]) +
                     ',' + str(self.position[1]), 'utf-8')

        lobby_uuid = ""  # we won't have a lobby_id, this is for DTN purposes
        player_uuid = ""  # we won't have a player_id, this is for DTN purposes

        ip = ip_address(MCAST_GROUP).exploded
        ip_dest = struct.pack('!8H', *[int(part, 10)
                              for part in ip.split(':')])

        payload = Payload(KALIVE, data, lobby_uuid,
                          player_uuid, 0, ip_src, ip_dest)

        return payload.to_bytes()

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
    def in_socket(self) -> socket:
        """
        The socket through which the gateway node receives messages from the DTN.
        """
        in_sock = socket(AF_INET6, SOCK_DGRAM)
        in_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        in_sock.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1)
        in_sock.bind(('', self.port))
        in_sock.settimeout(2)
        return in_sock

    @cached_property
    def out_socket(self) -> socket:
        """
        The socket through which the gateway node sends messages to the DTN.
        """
        out_sock = socket(AF_INET6, SOCK_DGRAM)
        out_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        out_sock.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1)
        out_sock.bind(('', self.port))
        out_sock.settimeout(2)
        return out_sock

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

    @cached_property
    def mcast_addr(self) -> Address:
        """
        The address used to send messages to the DTN.
        """
        return (getaddrinfo(MCAST_GROUP, None)[0][4][0], MCAST_PORT)

    def _broadcast_kalive(self):
        """
        KALIVE message broadcast.

        This message is used to inform mobile nodes that the gateway node is still alive.
        TODO: Mobile nodes will use this message to determine the amount of jumps that have been made.
        """

        while self.running:
            logging.info('Broadcasting KALIVE')
            # TODO: Requires all mobiles nodes to use the same port? Check this.
            self.msender.sendto(self.kalive, self.mcast_addr)
            time.sleep(1)

    def handle_kalive(self, addr: Address, payload: Payload) -> Payload:
        """
        Handles KALIVE messages.
        """
        try:
            # only mobile nodes send data in the KALIVE messages
            if payload.data is not None:

                if addr in self.mobile_nodes:
                    timestamp = time.time()
                    hops = 3 - payload.ttl
                    # payload's data to str
                    _x, _y = payload.data.decode('utf-8').split(',')
                    position = (float(_x), float(_y))
                    # get distance between the node and the gateway node
                    distance = get_node_distance(position, self.position)
                    # update the node's data
                    self.mobile_nodes[addr] = (
                        distance, position, timestamp, hops)
        except Exception as e:
            logging.error('Failed to handle KALIVE message: {}'.format(e))

        # null the payload's data
        payload.data = b''

        return payload

    def _get_preferred_node(self, destination: Optional[Address] = None) -> Address:
        """
        Returns a node.

        :return: The node with the lowest distance to the gateway node aswell as a low number of hops.
        """

        if destination is None:
            # return the closest node to us
            return min(self.mobile_nodes, key=lambda x: self.mobile_nodes[x][0])
        else:
            # get the destination node's position
            destination_position = self.mobile_nodes[destination][1]
            # get the distance between the gateway node and the destination node
            destination_distance = get_node_distance(
                destination_position, self.position)

            # create a dict of all addresses and their distances to the destination node
            # do not include the destination node
            distances = {
                addr: get_node_distance(
                    self.mobile_nodes[addr][1], destination_position)
                for addr in self.mobile_nodes
                if addr != destination
            }

            # find the address with the lowest distance to the destination node
            closest = min(distances, key=lambda x: distances[x])

            # if the closest node is closer than the destination node, return it
            if distances[closest] < destination_distance:
                return closest
            else:
                return destination

    def _handle_metric_updates(self):
        """
        Handles metric updates.
        """
        while self.running:
            # Every 3 seconds update the preffered mobile node and set it's address as the default.
            if time.time() - self.last_update > 3:
                self.last_update = time.time()

                self.preferred_mobile = self._get_preferred_node()

                self.preferred_mobile_addr = self.preferred_mobile[0]
                logging.info('Preferred mobile node is {}'.format(
                    self.preferred_mobile_addr))

            time.sleep(1)

        pass

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

                logging.info('Sent message to mobile node.')

            time.sleep(1)

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
        Main loop of the gateway node.
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
        logging.info('Leaving gateway node')

    def terminate(self, reason: str = "Unknown"):
        """
        Method used to close the gateway node.

        :param reason: The reason for closing the node.
        """

        logging.info('Terminating gateway node: {}'.format(reason))
        self.running = False
        self.leave()
