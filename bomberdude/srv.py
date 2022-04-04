import argparse
from server.server_cli import ServerCLI
from logging import INFO, DEBUG, ERROR

if __name__ == '__main__':
    """
    Start the bomberdude server.
    """
    parser = argparse.ArgumentParser(description='Bomberdude server.')
    parser.add_argument('-p', '--port', type=int, default=8080,)
    args = parser.parse_args()

    srv = ServerCLI(args.port, INFO)
    srv.start()
