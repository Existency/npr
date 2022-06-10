from __future__ import annotations
from dataclasses import dataclass, field
from threading import Lock
from typing import List, Tuple, Dict
import logging
import time
from copy import copy
from .payload import Payload
from .types import Address, SeqNum, Time

AddrCache = List[Tuple[Payload, Time]]
"""Each address has a list of tuples of payloads and timestamps."""
InnerCache = Dict[Address, AddrCache]
"""A node's cache."""


@dataclass
class Cache:
    """
    The cache is the main component of the algorithm.
    """
    cache_timeout: int
    level: int = field(default=logging.INFO)
    not_sent: InnerCache = field(default_factory=dict, init=False)
    sent: InnerCache = field(default_factory=dict, init=False)
    lock: Lock = field(default_factory=Lock, init=False)

    def __post_init__(self):
        logging.basicConfig(
            level=self.level, format='%(levelname)s: %(message)s')
        logging.info('Cache initialized')

    def __hash__(self) -> int:
        return hash(self.sent)

    def purge_timeout(self):
        """
        Purge all entries that have timed out.
        """
        cur_time = time.time()
        logging.info(f"Purging entries that have timed out")
        with self.lock:
            def timedout(x): return x[1][2] + self.cache_timeout < cur_time
            self.sent = {k: v for k, v in self.sent.items() if not timedout(v)}
            self.not_sent = {k: v for k,
                             v in self.not_sent.items() if not timedout(v)}

    def purge_entry(self, address: Address, payload: Payload):
        """
        Removes a specific entry from the cache.

        :param address: The address of the entry to purge.
        """
        with self.lock:
            # remove the entry from the sent cache
            logging.debug(f"Purging entry from {address}'s sent cache")
            if address in self.sent:
                self.sent[address] = [
                    (p, t) for p, t in self.sent[address] if p != payload]

            if address in self.not_sent:
                self.not_sent[address] = [
                    (p, t) for p, t in self.not_sent[address] if p != payload]

    def add_sent_entry(self, address: Address, payload: Payload):
        """
        Add an entry to the sent cache.

        :param address: The address of the entry.
        :param payload: The payload of the entry.
        """
        with self.lock:
            # add the entry to the sent cache
            logging.debug(f"Adding entry to {address}'s sent cache")
            if address in self.sent:
                self.sent[address].append((payload, time.time()))
            else:
                self.sent[address] = [(payload, time.time())]

    def add_entry(self, address: Address, payload: Payload):
        """
        Add an entry to the not_sent cache.

        :param address: The address of the entry.
        :param payload: The payload of the entry.
        """

        # add the entry to the sent cache
        logging.info(f"Adding entry to {address}'s not_sent cache")
        if address in self.not_sent:
            self.not_sent[address].append((payload, time.time()))
        else:
            self.not_sent[address] = [(payload, time.time())]

    def get_entries_not_sent(self) -> List[Tuple[Address, Payload]]:
        """
        Get all entries that weren't sent and adds them to the sent cache.

        :param address: The address to get entries from.
        :return: A list of entries.
        """
        with self.lock:
            entries = []
            for addr, payloads in self.not_sent.items():
                for payload, _ in payloads:
                    entries.append((addr, payload))
                    # add the entries to the sent cache
                    self.add_sent_entry(addr, payload)

            return entries

    def get_entries_sent_by(self, address: Address) -> List[Payload]:
        """
        Get all entries from a specific address.

        :param address: The address to get entries from.
        :return: A list of entries.
        """
        with self.lock:
            entries = []
            for addr, payloads in self.sent.items():
                if addr == address:
                    for payload, _ in payloads:
                        entries.append(payload)

            return entries

    def get_entries_sent(self) -> List[Tuple[Address, Payload]]:
        """
        Get all entries from all addresses.

        :return: A list of entries.
        """
        with self.lock:
            entries = []
            for addr, payloads in self.sent.items():
                for payload, _ in payloads:
                    entries.append((addr, payload))

            return entries
