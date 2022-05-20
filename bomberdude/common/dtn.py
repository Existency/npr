"""
Collection of methods to interact within a DTN.

These methods will replace the current ones within networking.py in mobile nodes.
"""
import time
import logging
from typing_extensions import Self

from .payload import Payload, KALIVE
from client.networking import NetClient

# Metrics
# - Packet loss
# - Packet delivery
# - Packet delivery rate
# - Packet delivery time
# - Distance to gateway node (hop count)
# - Number of KALIVE packets received
