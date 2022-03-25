from __future__ import annotations
import json
from threading import Thread, Lock
from socket import socket, AF_INET6, SOCK_DGRAM
from typing import Optional, Tuple
from logging import Logger


class NetClient:
    lobby_id: str  # in case multiple lobbies are implemented
    uuid: str
    lock: Lock
    port: int
    remote: Tuple[str, int]
    sock: ThreadedSocket
    queue: list
    logger: Logger

    def __init__(self, remote: Tuple[str, int], port: int):
        self.lobby_id = ''
        self.lock = Lock()
        self.port = port
        self.remote = remote
        self.queue = []
        self.logger = Logger('NetClient')
        self.logger.info('Client init\'d')

    def join(self, lobby_id: str):
        """
        Joins the server, upon joining the ThreadedSocket will start listening.
        """
        payload = json.dumps({'action': 'join', 'lobby': lobby_id, "uuid": ''})

        sock = socket(AF_INET6, SOCK_DGRAM)
        sock.bind(('', self.port))
        sock.setblocking(False)
        sock.sendto(payload.encode(), self.remote)

        while True:
            try:
                resp, addr = sock.recvfrom(1024)

                if addr == self.remote:
                    if resp:
                        data = json.loads(resp)
                        if data['action'] == 'joined':
                            self.uuid = data['uuid']
                            self.lobby_id = data['lobby']
                            self.sock = ThreadedSocket(sock, self.lock, self)
                            self.sock.start()
                            self.logger.info('Client joined lobby')
                            return True
                        else:
                            self.logger.warning(
                                'Server returned invalid action')
                            return False
                    else:
                        self.logger.warning('Server returned empty response')
                        return False
                else:
                    continue

            except Exception as e:
                pass

    def leave(self):
        """
        Method used to leave the game.
        """

        self.logger.info('Client leaving lobby by user request.')
        payload = json.dumps({'action': 'leave', 'uuid': self.uuid})
        self.send(payload.encode())

        # terminate the threaded socket
        self.sock.terminate()
        self.sock.join()

    def send(self, data: bytes):
        """
        Method used to send data to the server.

        :param data: The payload to be sent.
        """
        # TODO: should we keep this socket open?
        sock = socket(AF_INET6, SOCK_DGRAM)
        sock.sendto(data, self.remote)
        sock.close()

    def handle_data(self, data: bytes):
        """
        Method used to process data received from the server.

        :param data: The data payload to be handled.
        """
        try:
            data = json.loads(data)
            # TODO
            # parse the events
            # add it to the queue
            # the UI client / game loop will later process the queue

            return data
        except json.JSONDecodeError:
            print('Invalid JSON received')

    @property
    def messages(self) -> list:
        """
        Method used to get messages tuples from the queue.
        """
        with self.lock:
            message: list = self.queue
            self.queue = []
            return message

    def close(self):
        """
        Method used to close the client.
        """
        self.leave()
        self.sock.terminate()
        self.sock.join()


class ThreadedSocket(Thread):
    lock: Lock
    sock: socket
    client: NetClient

    def __init__(self, sock: socket, lock: Lock, client: NetClient):
        Thread.__init__(self)
        self.lock = lock
        self.sock = sock
        self.client = client

    def run(self):
        """
        Main loop to communicate with the client.
        """

        while True:
            data = b''
            data, addr = self.sock.recvfrom(1024)
            with self.lock:
                self.client.queue.append((data, addr))

    def terminate(self):
        """
        Terminates the client
        """
        self.sock.close()


# TODO: Implement tests for these.
