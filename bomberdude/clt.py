import argparse
import time
from client.networking import NetClient

if __name__ == '__main__':
    """
    Start the bomberdude client.
    """

    client = NetClient(('', 8080), 8808)
    client.start()

    while True:
        time.sleep(1)
