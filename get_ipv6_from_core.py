from xml.dom import minidom
from os import listdir
from os.path import isdir, join
from typing import Optional
from ipaddress import ip_address
import struct


def get_node_ipv6(id: str):
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

        # select the element whose name is n1
        el = None

        for element in elements:
            if element.getAttribute('name') == id:
                el = element
                break

        if el is not None:
            return el.getElementsByTagName('address')[1].firstChild.nodeValue


ip = ip_address(get_node_ipv6('n1')).exploded
print('The original IPv6 address is: ' + ip)

# split the ip address

packed_ip = struct.pack('!8H', *[int(part, 10) for part in ip.split(':')])

print('The packed ip is: {!r}'.format(packed_ip))
print('The number of bytes is: {}'.format(len(packed_ip)))
print('Type of packed_ip is: {}'.format(type(packed_ip)))

ip_dest = struct.pack('!8H', *[int(part, 16)
                               for part in ip_address('ff02::1').exploded.split(':')])

print('The packed ip is: {!r}'.format(ip_dest))
