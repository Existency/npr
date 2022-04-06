import argparse
import time
from client.networking import NetClient

if __name__ == '__main__':
    """
    Start the bomberdude client.
    """
    parser = argparse.ArgumentParser(description='Bomberdude client.')
    parser.add_argument('-p', '--port', type=int, default=8081,)
    parser.add_argument('-i', '--id', type=str, default='',)
    args = parser.parse_args()

    client = NetClient(('::1', 8080), args.port)
    client.join_server(args.id)
    client.start()
