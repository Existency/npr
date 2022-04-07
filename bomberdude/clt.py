#!/usr/bin/env python3

import argparse
from client.networking import NetClient
from logging import INFO, DEBUG, ERROR, WARNING

if __name__ == '__main__':
    """
    Start the bomberdude server.
    """
    parser = argparse.ArgumentParser(description='Bomberdude server.')
    parser.add_argument('-p', '--port', type=int, default=8090,)
    parser.add_argument('-n', '--name', type=str, default='anonymous')
    parser.add_argument('-a', '--address', type=str, default='::1')
    parser.add_argument('-i', '--id', type=str, default='')
    parser.add_argument('-l', '--level', type=str, default='info',)

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

    cli = NetClient((args.address, 8080), args.port, level=log_lvl)
    cli.join_server(args.id)
    cli.start()
