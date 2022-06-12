from typing import Tuple, Dict

# Type aliases that are common to nearly all components.
# Defined here so that changes can be made to the types without
# having to change all components and avoid breakage of the system.

# No clue whether this is a good practice.

Address = Tuple[str, int]
"""The IPv6 address of a node."""

Time = float
"""The time when a Payload was sent or received in milliseconds."""

SeqNum = int
"""The Payload's sequence number."""

Position = Tuple[float, float]
"""The (x, y) coordinates of a node."""

Distance = float
"""The distance between two nodes."""

Hops = int
"""The estimated number of hops between two nodes."""

MobileMetrics = Tuple[Distance, Position, Time, Hops]
"""
    Distance: The distance between the mobile node and the edge node.
    Position: The (x, y) coordinates of the edge node.
    Time: The time when the mobile node last sent a message.
    Hops: The number of hops the mobile node's data has made.
"""

MobileMap = Dict[Address, MobileMetrics]
"""
    Address: The node's address.
    MobileData: The node's data.
"""

# MCAST_GROUP = "ff02::1"
MCAST_GROUP = 'ff15:1234:5678:9101:1121:3141:5161:0001'
"""Used to send and receive multicast messages within the DTN."""

MCAST_PORT = 9998
"""Port used by the DTN nodes."""

DEFAULT_PORT = 9999

TIMEOUT = 10

###############################################
# NDN specific types                          #
###############################################

Interface = Address
"""The address of the interface."""

Prefix = str
"""A prefix leading to data."""

# NDN Packet types
PACKET_TYPE_DATA = 0
PACKET_TYPE_INTEREST = 1
NDNPacketType = bool
"""Whether the packet is data or interest."""
