#!/usr/bin/env python3

import argparse
from server.server_cli import ServerCLI
from logging import INFO, DEBUG, ERROR, WARNING

if __name__ == '__main__':
    """
    Start the bomberdude server.
    """
    parser = argparse.ArgumentParser(description='Bomberdude server.')
    parser.add_argument('--id', type=str, required=True,)
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

    srv = ServerCLI(log_lvl, args.id)
    srv.start()
