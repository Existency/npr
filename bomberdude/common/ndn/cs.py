from threading import Thread
from typing import Dict, Optional
from dataclasses import dataclass, field
from common.types import Prefix
import time


@dataclass
class ContentStoreCache:
    cache_timeout: int
    """The timeout of the cache in seconds."""
    cache: Dict[Prefix, list] = field(default_factory=dict, init=False)
    """The content store cache contains all the bytes received for a given prefix."""

    def __hash__(self) -> int:
        return super().__hash__()

    def __init__(self, cache_timeout: int):
        self.cache_timeout = cache_timeout

    def add(self, prefix: Prefix, data: bytes):
        """
        Add a new entry to the content store cache
        """
        if prefix not in self.cache:
            self.cache[prefix] = [data, time.time()]

    def lookup(self, prefix: Prefix) -> Optional[bytes]:
        """
        Lookup a prefix in the content store cache
        """
        if prefix in self.cache:
            self.cache[prefix][1] = time.time()
            return self.cache[prefix][0]
        return None

    def clear_expired(self):
        """
        Remove all expired entries from the content store cache
        """
        for prefix in list(self.cache):
            if time.time() - self.cache[prefix][1] > self.cache_timeout:
                del self.cache[prefix]


@dataclass
class ContentStore:
    cache_timeout: int = field(default=20)
    """The timeout of the packets in the content store."""

    cache: ContentStoreCache = field(init=False)
    """The cache of the content store."""

    def __hash__(self) -> int:
        return super().__hash__()

    def __post_init__(self):
        self.cache = ContentStoreCache(self.cache_timeout)

    def _handle_cache_timeout(self):
        """
        Clears the cache of expired entries
        """
        while True:
            self.cache.clear_expired()
            time.sleep(1)

    def add(self, prefix: Prefix, data: bytes):
        """
        Add a new entry to the content store
        """
        self.cache.add(prefix, data)

    def lookup(self, prefix: Prefix) -> Optional[bytes]:
        """
        Lookup a prefix in the content store
        """
        return self.cache.lookup(prefix)

    def run(self):
        """
        Run the content store
        """
        Thread(target=self._handle_cache_timeout).start()
