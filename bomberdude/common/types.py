from typing import Tuple

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
