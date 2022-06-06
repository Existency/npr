#!/usr/bin/env python3

import argparse
from client.networking import NetClient
from client.client import Client
from common.core_utils import get_node_ipv6, get_node_path
from logging import INFO, DEBUG, ERROR, WARNING

if __name__ == '__main__':
    """
    Start the bomberdude server.
    """
    parser = argparse.ArgumentParser(description='Bomberdude server.')
    parser.add_argument('-n', '--name', type=str, default='anonymous')
    parser.add_argument('-a', '--address', type=str, required=True)
    parser.add_argument('-i', '--id', type=str, required=True)
    parser.add_argument('-l', '--level', type=str, default='info',)
    parser.add_argument('-g', '--gateway', type=str, required=True)

    args = parser.parse_args()

    # parse level
    if args.level == 'debug':
        log_lvl = DEBUG
    elif args.level == 'error' or args.level == 'err':
        log_lvl = ERROR
    elif args.level == 'warning' or args.level == 'warn':
        log_lvl = WARNING
    else:
        log_lvl = INFO

    # get node's path
    node_path = get_node_path(args.id)

    if node_path is None:
        print("Node's path not found")
        exit(1)

    node_ipv6 = get_node_ipv6(args.id)
    if node_ipv6 is None:
        print("Node's ipv6 not found")
        exit(1)

    print("node_ipv6", node_ipv6)
    pymenu = Client(args, node_path, node_ipv6)
    pymenu.start_game()

    # cli = NetClient((args.address, 8080), args.port,
    #                 level=log_lvl, npath=node_path)
    # cli.join_server(args.id)
    # cli.start()
