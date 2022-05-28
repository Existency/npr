from ast import Bytes
from ipaddress import ip_address
from xml.dom import minidom
from os import listdir
from os.path import isdir, join
from typing import Optional
from .types import Position
import struct


def get_node_path(id: str) -> Optional[str]:
    """
    Finds the path to a node's .xy file in the /tmp/pycore.* directory.

    :param id: The id of of the node
    :return: The path to the node's .xy file
    """
    try:
        rootdir = "/tmp/"
        # get all folders that contain 'pycore'
        instances = [f for f in listdir(rootdir) if isdir(
            join(rootdir, f)) and 'pycore' in f]

        # get the first pycore
        if len(instances) > 0:
            pycore = join(rootdir, instances[0])
            return join(pycore, id + '.xy')
    except:
        pass

    return None


def get_node_xy(path: str) -> Position:
    """
    Returns the xy coordinates of a node in the /tmp/pycore.*/ directory.

    :param id: The id of of the node
    :return: The xy coordinates of the node
    """
    # the file's content is a single line with the xy coordinates
    # Error checking wasn't implemented as the file should always exist

    with open(path, 'r') as f:
        content = f.read()
        # split the line into two parts
        coords = content.split(',')
        # return the xy coordinates
        return (float(coords[0]), float(coords[1]))


def get_node_distance(n1: Position, n2: Position) -> float:
    """
    Returns the distance between two nodes.

    :param n1: The xy coordinates of the first node
    :param n2: The xy coordinates of the second node
    :return: The distance between the two nodes
    """
    return ((n1[0] - n2[0]) ** 2 + (n1[1] - n2[1]) ** 2) ** 0.5


def get_node_ipv6(id: str) -> Optional[bytes]:
    """
    Get the IPv6 address of the node with the given path.

    :param path: The path of the node.
    :return: The IPv6 address of the node or None if the node was not found.
    """

    rootdir = "/tmp/"
    # get all folders that contain 'pycore'
    instances = [f for f in listdir(rootdir) if isdir(
        join(rootdir, f)) and 'pycore' in f]

    # get the first pycore
    if len(instances) > 0:
        pycore = join(rootdir, instances[0])
        path = join(pycore, 'session-deployed.xml')

        root = minidom.parse(path)

        container = root.getElementsByTagName('container')[0]
        test_host = container.getElementsByTagName('testHost')[0]
        elements = test_host.getElementsByTagName('testHost')

        for element in elements:
            if element.getAttribute('name') == id:
                ip = element.getElementsByTagName(
                    'address')[0].firstChild.nodeValue

                ip = ip_address(ip).exploded

                # split the ip address
                ip_parts = [int(part, 10) for part in ip.split(':')]
                return struct.pack('!8H', *ip_parts)

    return None


def explode_ipv6(ipv6: str) -> str:
    """
    Explode an IPv6 address into a readable string.

    :param ipv6: The IPv6 address to explode.
    :return: The exploded IPv6 address.
    """
    return ip_address(ipv6).exploded


def compress_ipv6(ipv6: str) -> str:
    """
    Compress an IPv6 address into a readable string.

    :param ipv6: The IPv6 address to compress.
    :return: The compressed IPv6 address.
    """
    return ip_address(ipv6).compressed
