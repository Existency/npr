from typing import Dict, List
from common.types import Address

Name = str


class ForwardingInformationBase:
    """
    Forwarding Information Base (FIB)

    The Forwarding Information Base (FIB) is a table of all the names
    and the ifaces that are currently known to be reachable. 

    Will be used to determine which iface to use
    when sending or requesting data.
    """
    base: Dict[Name, List[Address]]
    """A database of names and the addresses through which they are reachable."""

    def __init__(self):
        self.base = {}

    def add(self, name, face):
        """
        Add a new entry to the FIB
        """
        if name not in self.base:
            self.base[name] = []
        self.base[name].append(face)

    def remove(self, name, face):
        """
        Remove an entry from the FIB
        """
        if name in self.base and face in self.base[name]:
            self.base[name].remove(face)
            if len(self.base[name]) == 0:
                del self.base[name]

    def lookup(self, name):
        """
        Lookup a name in the FIB
        """
        if name in self.base:
            return self.base[name]
        return []
