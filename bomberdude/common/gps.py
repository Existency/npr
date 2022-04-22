from os import listdir
from os.path import isdir, join
from typing import Optional, Tuple


def get_node_path(id: str) -> Optional[str]:
    """
    Finds the path to a node's .xy file in the /tmp/pycore.* directory.

    :param id: The id of of the node
    :return: The path to the node's .xy file
    """
    # get the current pycore
    rootdir = "/tmp/"
    # get all folders that contain 'pycore'
    pycores = [f for f in listdir(rootdir) if isdir(
        join(rootdir, f)) and 'pycore' in f]

    # get the first pycore
    if len(pycores) > 0:
        pycore = join(rootdir, pycores[0])
        return join(pycore, id + '.xy')

    return None


def get_node_xy(path: str) -> Tuple[float, float]:
    """
    Returns the xy coordinates of a node in the /tmp/pycore.*/ directory.

    :param id: The id of of the node
    :return: The xy coordinates of the node
    """
    # the file's content is a single line with the xy coordinates
    with open(path, 'r') as f:
        content = f.read()
        # split the line into two parts
        coords = content.split(',')
        # return the xy coordinates
        return (float(coords[0]), float(coords[1]))
