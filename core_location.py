#!/bin/python3

import argparse
from os import listdir
from os.path import isdir, join


def get_node_path(id):
    """
    Finds the path to a node's .xy file in the /tmp/pycore.* directory.

    :param id: The node's id.
    :return: The path to the node's '.xy' file.
    """

    # get the current pycore
    rootdir = "/tmp/"
    # CORE creates temporary directories in /tmp/
    # The name of a directory is /tmp/pycore.N, where N is the id of a running instance of CORE
    instances = [f for f in listdir(rootdir) if isdir(
        join(rootdir, f)) and 'pycore' in f]

    if len(instances) > 0:
        # We'll select the first directory in the list of directories in /tmp/ that fits the criteria
        pycore = join(rootdir, instances[0])
        return join(pycore, id + '.xy')

    return None


def get_node_xy(path):
    """
    Returns a node's (x,y) coordinates.

    :param id: The string id of of the node
    :return: The (x,y) coordinates of the node
    """
    # the file's content is a single line with the xy coordinates
    with open(path, 'r') as f:
        content = f.read()
        # split the line into two parts
        coords = content.split(',')
        # return the xy coordinates
        return (float(coords[0]), float(coords[1]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Get the xy coordinates of a node')
    parser.add_argument('-n', '--name', help='The node\'s name.')

    args = parser.parse_args()

    path = get_node_path(args.id)

    if path is not None:
        while True:
            position = get_node_xy(path)
            if position is not None:
                print(position)
    else:
        print('Node with id ' + args.id + ' wasn\'t  found.')
