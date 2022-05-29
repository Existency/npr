from __future__ import annotations
from dataclasses import dataclass, field
from functools import singledispatchmethod
from threading import Lock
from typing import List, Tuple, Dict
import logging
import time
from .payload import Payload
from .types import Address, SeqNum, Time

CacheEntry = Tuple[Address, Payload, Time]
"""A line of cache, contains the address, payload, time and whether it was sent or not."""

InnerCache = Dict[SeqNum, CacheEntry]
"""A Node's cache."""


@dataclass
class Cache:
    """
    The cache is the main component of the algorithm.
    """
    # seq_num: (address, payload, timestamp)
    # TODO: change from a HashMap<seqnum, (addr, payload, timestamp)> to HashMap<address, Vec<(payload, timestamp)>>
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

        with self.lock:
            for seq_num, (addr, _, timestamp) in self.sent.items():
                if cur_time - timestamp > self.cache_timeout:
                    logging.debug(
                        f"Purging entry {seq_num} meant for {addr} from cache")

    @singledispatchmethod
    def purge_entries(self):
        """
        Purge all entries from the cache.
        """
        with self.lock:
            logging.info(f"Purging all entries from cache")
            self.sent.clear()

    @purge_entries.register
    def _(self, seq_num: SeqNum, address: Address):
        """
        Purge a specific entry from the cache.

        :param seq_num: The sequence number of the entry to purge.
        :param address: The address of the entry to purge.
        """
        with self.lock:
            # purge the entry that matches the sequence number and address
            for seq_num, (addr, _, _) in self.sent.items():
                if seq_num == seq_num and addr == address:
                    logging.debug(f"Purging entry {seq_num} from cache")
                    # fun fact, did you know that del doesn't throw exceptions? Keeps them silent. :D
                    del self.sent[seq_num]
                    break

    def add_sent_entry(self, seq_num: SeqNum, address: Address, payload: Payload):
        """
        Add an entry to the sent cache.

        :param seq_num: The sequence number of the entry.
        :param address: The address of the entry.
        :param payload: The payload of the entry.
        """
        with self.lock:
            logging.debug(f"Adding entry {seq_num} to cache")
            self.sent[seq_num] = (address, payload, time.time())

    def add_entry(self, seq_num: SeqNum, address: Address, payload: Payload):
        """
        Add an entry to the not_sent cache.

        :param seq_num: The sequence number of the entry.
        :param address: The address of the entry.
        :param payload: The payload of the entry.
        """
        with self.lock:
            logging.debug(f"Adding entry {seq_num} to cache")
            self.not_sent[seq_num] = (address, payload, time.time())

    # add multiple entries at once
    def add_entries(self, entries: List[Tuple[SeqNum, Address, Payload, Time]]):
        """
        Add multiple entries to the cache.

        :param entries: A tuple list containing seqnum, address, payload and time.
        """
        with self.lock:
            for seq_num, address, payload, timestamp in entries:
                logging.debug(f"Adding entry {seq_num} to cache")
                self.not_sent[seq_num] = (address, payload, timestamp)

    @singledispatchmethod
    def get_entries_not_sent(self, address: Address) -> List[CacheEntry]:
        """
        Get all entries from a specific address.

        :param address: The address to get entries from.
        :return: A list of entries.
        """
        with self.lock:
            entries = []
            for seq_num, (addr, payload, time) in self.not_sent.items():
                # move the entry to the sent cache and append it to the list
                if addr == address:
                    logging.debug(f"Getting entry {seq_num} from cache")
                    self.sent[seq_num] = (addr, payload, time)
                    entries.append((addr, payload, time))
                    del self.not_sent[seq_num]
            return entries

    @get_entries_not_sent.register
    def _(self) -> List[CacheEntry]:
        """
        Get all entries from all addresses.

        :return: A list of entries.
        """
        # get all entries in the dictionary as a list
        entries = []
        with self.lock:
            # move the values to the sent cache
            for seq_num, (addr, payload, time) in self.not_sent.items():
                logging.debug(f"Getting entry {seq_num} from cache")
                self.sent[seq_num] = (addr, payload, time)
                entries.append((addr, payload, time))
                del self.not_sent[seq_num]
        return entries

    @singledispatchmethod
    def get_entries_sent(self, address: Address) -> List[CacheEntry]:
        """
        Get all entries from a specific address.

        :param address: The address to get entries from.
        :return: A list of entries.
        """
        with self.lock:
            entries = []
            for seq_num, (addr, payload, time) in self.sent.items():
                if addr == address:
                    logging.debug(f"Getting entry {seq_num} from cache")
                    entries.append((addr, payload, time))
            return entries

    @get_entries_sent.register
    def _(self) -> List[CacheEntry]:
        """
        Get all entries from all addresses.

        :return: A list of entries.
        """
        with self.lock:
            entries = []
            for seq_num, (addr, payload, time) in self.sent.items():
                logging.debug(f"Getting entry {seq_num} from cache")
                entries.append((addr, payload, time))
            return entries
