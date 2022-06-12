from dataclasses import dataclass, field
from typing import Dict, List
from common.types import Interface, Prefix


@dataclass
class PendingInterestTable:
    """
    The Pending Interest Table (PIT) is a table of all the prefixes
    and the ifaces which have demonstrated interest.

    Will be used to direct the packets of data to the correct Ifaces.
    """
    table: Dict[Prefix, List[Interface]] = field(
        default_factory=dict, init=False)
    """A database of prefixes and the addresses that requested them."""

    def __hash__(self) -> int:
        return super().__hash__()

    def insert(self, name: Prefix, faceid: Interface):
        if name in self.table:
            self.table[name].append(faceid)
        else:
            self.table[name] = [faceid]

    def lookup(self, name: Prefix) -> List[Interface]:
        if name in self.table:
            return self.table[name]
        else:
            return []

    def remove(self, name: Prefix, faceid: Interface):
        if name in self.table:
            self.table[name].remove(faceid)
            if len(self.table[name]) == 0:
                del self.table[name]
