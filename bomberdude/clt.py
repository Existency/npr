import argparse
import time
from client.networking import NetClient

if __name__ == '__main__':
    """
    Start the bomberdude client.
    """
    parser = argparse.ArgumentParser(description='Bomberdude server.')
    parser.add_argument('-p', '--port', type=int, default=8080)
    parser.add_argument('-i', '--ip', type=str, default='')
    parser.add_argument('-r', '--rport', type=int, default=8080)
    args = parser.parse_args()

    client = NetClient((args.ip, args.rport), args.port)
    client.start()

    while True:
        time.sleep(1)
