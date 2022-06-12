from dataclasses import dataclass, field
from typing import Dict, List
from common.types import Interface, Prefix


@dataclass
class ForwardingInformationBase:
    """
    Forwarding Information Base (FIB)

    The Forwarding Information Base (FIB) is a table of all the names
    and the ifaces that are currently known to be reachable. 

    Will be used to determine which iface to use
    when sending or requesting data.
    """
    base: Dict[Prefix, List[Interface]] = field(
        default_factory=dict, init=False)
    """A database of names and the addresses through which they are reachable."""

    def __hash__(self) -> int:
        return super().__hash__()

    def add(self, name: Prefix, face: Interface):
        """
        Add a new entry to the FIB
        """
        if name not in self.base:
            self.base[name] = []
        self.base[name].append(face)

    def remove(self, name: Prefix, face: Interface):
        """
        Remove an entry from the FIB
        """
        if name in self.base and face in self.base[name]:
            self.base[name].remove(face)
            if len(self.base[name]) == 0:
                del self.base[name]

    def lookup(self, name: Prefix) -> List[Interface]:
        """
        Lookup a name in the FIB
        """
        if name in self.base:
            return self.base[name]
        return []
