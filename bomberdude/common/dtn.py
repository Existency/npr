from __future__ import annotations
from dataclasses import dataclass, field
from functools import singledispatchmethod
from threading import Lock
from typing import List, Optional, Tuple, Dict
from .payload import Payload
import logging
import time


@dataclass
class Cache:
    """
    The cache is the main component of the algorithm.
    """
    # seq_num: (address, payload, timestamp)
    cache: Dict[int, Tuple[Tuple[int, int], Payload, float]
                ] = field(default_factory=dict, init=False)
    lock: Lock = field(default_factory=Lock, init=False)

    def __hash__(self) -> int:
        return hash(self.cache)

    @singledispatchmethod
    def purge_entries(self):
        """
        Purge all entries from the cache.
        """
        with self.lock:
            logging.info(f"Purging all entries from cache")
            self.cache.clear()

    @purge_entries.register
    def _(self, seq_num: int):
        """
        Purge a specific entry from the cache.

        :param seq_num: The sequence number of the entry to purge.
        """
        with self.lock:
            if seq_num in self.cache:
                logging.info(f"Purging entry {seq_num} from cache")
                del self.cache[seq_num]

    @purge_entries.register
    def _(self, address: Tuple[int, int]):
        """
        Purge all entries from a specific address.

        :param address: The address to purge.
        """
        with self.lock:
            for seq_num, (addr, _, _) in self.cache.items():
                if addr == address:
                    logging.debug(f"Purging entry {seq_num} from cache")
                    del self.cache[seq_num]

    @singledispatchmethod
    def add_entry(self, seq_num: int, address: Tuple[int, int], payload: Payload, timestamp: float):
        """
        Add an entry to the cache.

        :param seq_num: The sequence number of the entry.
        :param address: The address of the entry.
        :param payload: The payload of the entry.
        :param timestamp: The timestamp of the entry.
        """
        with self.lock:
            logging.debug(f"Adding entry {seq_num} to cache")
            self.cache[seq_num] = (address, payload, timestamp)

    @add_entry.register
    def _(self, seq_num: int, address: Tuple[int, int], payload: Payload):
        """
        Add an entry to the cache.

        :param seq_num: The sequence number of the entry.
        :param address: The address of the entry.
        :param payload: The payload of the entry.
        """
        with self.lock:
            logging.debug(f"Adding entry {seq_num} to cache")
            self.cache[seq_num] = (address, payload, time.time())

    # add multiple entries at once
    def add_entries(self, entries: List[Tuple[int, Tuple[int, int], Payload, float]]):
        """
        Add multiple entries to the cache.

        :param entries: A list of entries.
        """
        with self.lock:
            for seq_num, address, payload, timestamp in entries:
                logging.debug(f"Adding entry {seq_num} to cache")
                self.cache[seq_num] = (address, payload, timestamp)

    def get_entries(self, address: Tuple[int, int]) -> List[Tuple[Tuple[int, int], Payload, float]]:
        """
        Get all entries from a specific address.

        :param address: The address to get entries from.
        :return: A list of entries.
        """
        with self.lock:
            entries = []
            for seq_num, (addr, _, _) in self.cache.items():
                if addr == address:
                    logging.debug(f"Getting entry {seq_num} from cache")
                    entries.append(self.cache[seq_num])
            return entries
