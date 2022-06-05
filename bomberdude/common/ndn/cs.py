from dataclasses import dataclass, field
from socket import timeout
from common.cache import Cache


@dataclass
class ContentStore:
    cache_timeout: int = field(default=10)
    """The timeout of the packets in the content store."""

    cache: Cache = field(init=False)
    """The cache of the content store."""

    def __post_init__(self):
        self.cache = Cache(self.cache_timeout)

    # TODO: implement gets and pushes
