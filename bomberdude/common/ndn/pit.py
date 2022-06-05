from typing import Dict, List
from common.types import Address

Name = str


class PendingInterestTable:
    """
    The Pending Interest Table (PIT) is a table of all the prefixes
    and the ifaces which have demonstrated interest.

    Will be used to direct the packets of data to the correct Ifaces.
    """
    table: Dict[Name, List[Address]]
    """A database of prefixes and the addresses that requested them."""

    def __init__(self):
        self.table = {}

    def insert(self, name, faceid):
        if name in self.table:
            self.table[name].append(faceid)
        else:
            self.table[name] = [faceid]

    def lookup(self, name):
        if name in self.table:
            return self.table[name]
        else:
            return []

    def remove(self, name, faceid):
        if name in self.table:
            self.table[name].remove(faceid)
            if len(self.table[name]) == 0:
                del self.table[name]
