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
from socket import IPPROTO_IPV6, IPPROTO_UDP, IPV6_JOIN_GROUP, IPV6_MULTICAST_HOPS, getaddrinfo, socket, AF_INET6, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR, SO_REUSEPORT, inet_pton, getaddrinfo, timeout
from threading import Thread, Lock
from typing import Optional

from common.payload import GKALIVE, Payload
from common.types import DEFAULT_PORT, MCAST_GROUP, MCAST_PORT, Position, Address, MobileMap
from common.cache import Cache
from common.core_utils import get_node_distance, get_node_xy


@dataclass
class EdgeNode(Thread):
    """
    gateway node for the DTN network.
    """
    server_address: Address
    """The server's address"""

    node_path: str
    """The node's system path (CORE related)."""

    gateway_dtn_address: bytes
    """The address used to interact with the DTN"""

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

    outgoing_server: Cache = field(init=False)
    """Messages meant for the server."""

    preferred_mobile: Optional[Address] = field(init=False, default=None)

    # TODO: Use ttl aswell as the coordinates as a metric to determine whether a node is stale.

    #       Modify the way broadcasts are made in the mobile nodes (networking.py).
    #       Include the  coordinates in the KALIVE message.
    #       Edge will remove coordinates from KALIVE messages before sending to server.

    def __hash__(self) -> int:
        return super().__hash__()

    def __post_init__(self):
        super(EdgeNode, self).__init__()
        logging.basicConfig(
            level=self.level, format='%(levelname)s: %(message)s')

        # Create the outgoing cache
        self.outgoing_mobile = Cache(self.cache_timeout, level=self.level)
        self.outgoing_server = Cache(self.cache_timeout, level=self.level)

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

        ip_src = ip_address(self.gateway_dtn_address).exploded
        ip_dest = ip_address(MCAST_GROUP).exploded

        # ip_src = ip_address(self.gateway_dtn_address).exploded.encode('utf-8')
        # ip_src = struct.pack('!16s', ip_src)
        # ip = ip_address(MCAST_GROUP).exploded.encode('utf-8')
        # ip_dest = struct.pack('!16s', ip)
        
        
        data = bytes(str(self.position[0]) +
                     ',' + str(self.position[1]), 'utf-8')

        lobby_uuid = ""  # we won't have a lobby_id, this is for DTN purposes
        player_uuid = ""  # we won't have a player_id, this is for DTN purposes

        payload = Payload(GKALIVE, data, lobby_uuid,
                          player_uuid, 0, inet_pton(AF_INET6, ip_src), inet_pton(AF_INET6, ip_dest))

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
        in_sock.bind(('', DEFAULT_PORT))
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
        out_sock.bind(('', DEFAULT_PORT))
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
            #logging.info('Broadcasting KALIVE')
            # TODO: Requires all mobiles nodes to use the same port? Check this.
            self.msender.sendto(self.kalive, self.mcast_addr)
            time.sleep(1)

    def handle_kalive(self, addr: Address, payload: Payload) -> Payload:
        """
        Handles KALIVE messages from mobile nodes.
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
                    logging.info('Received KALIVE from {}'.format(addr))
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

        while self.preferred_mobile is None:
            time.sleep(0.01)

        self.last_update = time.time()
        while self.running:
            # Every 5 seconds update the preffered mobile node and set it's address as the default.
            if time.time() - self.last_update > 5:
                self.last_update = time.time()

                self.preferred_mobile = self._get_preferred_node()
                logging.info('Preferred mobile node is {}'.format(
                    self.preferred_mobile[0]))

            time.sleep(1)

    def _handle_incoming_dtn(self):
        """
        Handles incoming IPv6 messages.
        """
        while self.running:
            try:
                data, addr = self.dtn_sock.recvfrom(1500)
                logging.info('Received from {}'.format(addr))

                address = (addr[0], addr[1])

                payload = Payload.from_bytes(data)

                if payload is None:
                    logging.warning(
                        'Received invalid payload from {}.'.format(address))
                    continue

                if payload.is_kalive:
                    payload = self.handle_kalive(address, payload)

            except timeout:
                continue
            except Exception as e:
                logging.error(
                    'Failed to handle incoming IPv6 message: {}'.format(e))
                continue

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
                data, addr = self.in_socket.recvfrom(1500)
                logging.info('Received {} from {}'.format(data, addr))

                address = (addr[0], addr[1])

                if self.preferred_mobile is None:
                    self.preferred_mobile = address

                payload = Payload.from_bytes(data)
                logging.debug(
                    'Received payload with type: {}'.format(payload.type_str))

                # Figure whether the message is from the server or from a mobile node
                if address == self.server_address:
                    # if the message is an ack, remove the data from the outgoing_server cache
                    if payload.is_ack:
                        # the message's destination is the address of the sender of the original message
                        destination = (payload.short_destination, DEFAULT_PORT)

                        self.outgoing_server.purge_entry(
                            destination, payload)

                    self.outgoing_mobile.add_entry(address, payload)
                    logging.info('Received message from server.')

                else:
                    # handle ACK messages
                    if payload.is_ack:
                        destination = (payload.short_destination, DEFAULT_PORT)

                        self.outgoing_mobile.purge_entry(
                            destination, payload)

                    with self.outgoing_srv_lock:
                        self.outgoing_server.add_entry(
                            address, payload)
                    logging.info(
                        'Received message from mobile node meant for server.')

            except timeout:
                continue

            except Exception as e:
                logging.error(e)
                continue

    def _handle_outgoing(self):
        """
        Handles the outgoing messages.
        """

        while self.preferred_mobile is None:
            time.sleep(0.01)

        while self.running:
            # Send messages to the server
            outgoing = []

            with self.outgoing_srv_lock:
                outgoing = self.outgoing_server.get_entries_not_sent()

            for (addr, payload) in outgoing:
                logging.debug('Sending payload to {}'.format(addr))
                self.out_socket.sendto(payload.to_bytes(), addr)

            # Send messages to the mobile nodes
            outgoing = self.outgoing_mobile.get_entries_not_sent()

            # get the preferred mobile node
            out_addr = self.preferred_mobile

            for (addr, payload) in outgoing:
                logging.debug(
                    'Sending payload to {} through {}.'.format(addr, out_addr))
                self.out_socket.sendto(payload.to_bytes(), out_addr)

            # TODO: Requires two changes that I can think of right now.
            #      1. The mobile nodes will need a local cache of nearby nodes, this way they can send messages to their neighbors.
            #      2. The same ACK system as on gateway.py#192 should be implemented on mobile nodes.

            time.sleep(0.033)

    def _handle_cache_timeout(self):
        """
        Every N seconds the cache is checked for messages that timed out.

        If a message has timed out, it is removed from the cache.
        """
        while self.running:
            self.outgoing_mobile.purge_timeout()
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
        logging.info('Handle incoming dtn thread started')
        Thread(target=self._handle_incoming_dtn).start()
        logging.info('Handle metrics thread started')
        Thread(target=self._handle_metric_updates).start()

        # Keep the main thread alive
        while self.running:
            time.sleep(1)

    def _on_leave_force_send(self):
        """
        Sends all the available outgoing messages to their destination.
        This is a last effort to try and makes sure all messages are delivered.
        This does not offer any guarantees that any of the messages will be delivered.
        """

        outgoing_server = self.outgoing_server.get_entries_not_sent() + \
            self.outgoing_server.get_entries_sent()

        outgoing_mobile = self.outgoing_mobile.get_entries_not_sent() + \
            self.outgoing_mobile.get_entries_sent()

        for (_, payload) in outgoing_server:
            logging.debug('Sending {} to {}'.format(
                payload, self.server_address))
            self.out_socket.sendto(payload.to_bytes(), self.server_address)

        out_addr = self._get_preferred_node()

        for (addr, payload) in outgoing_mobile:
            logging.debug('Sending {} to {} through {}.'.format(
                payload, addr, out_addr))
            self.out_socket.sendto(payload.to_bytes(), out_addr)

        pass

    def leave(self):
        """
        Attempt to send all messages to the network.

        Afterwards, the node will closed.
        """
        # Forcefully send all outgoing messages, even those already sent.
        self._on_leave_force_send()
        self.running = False
        logging.info('Leaving gateway node')

    def terminate(self, reason: str = "Unknown"):
        """
        Method used to close the gateway node.

        :param reason: The reason for closing the node.
        """
        logging.info('Terminating gateway node: {}'.format(reason))
        self.leave()
