from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple, List
from threading import Thread, Lock
from socket import socket, AF_INET6, SOCK_DGRAM
from logging import Logger
from common.payload import Payload, ACCEPT, LEAVE, JOIN


@ dataclass
class NetClient:
    port: int
    remote: Tuple[str, int]
    lobby_uuid: str = field(default_factory=str)  # init'd when joining a lobby
    sock: ThreadedSocket = field(init=False)  # init'd when joining a lobby
    lock: Lock = field(default_factory=Lock)
    queue: List[Tuple[bytes, Tuple[str, int]]] = field(default_factory=list)
    logger: Logger = field(init=False)
    player_uuid: str = field(default='')

    def __post_init__(self):
        self.logger = Logger('NetClient')
        self.logger.info('Client init\'d')

    def __init__(self, remote: Tuple[str, int], port: int):
        self.lobby_uuid = ''
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

        payload = Payload(JOIN, b'', lobby_id, '', 0)

        sock = socket(AF_INET6, SOCK_DGRAM)
        sock.bind(('', self.port))
        sock.setblocking(False)
        sock.sendto(payload.to_bytes(), self.remote)

        while True:
            try:
                resp, addr = sock.recvfrom(1024)

                if addr == self.remote:
                    if resp:
                        data = Payload.from_bytes(resp)

                        if data.type == ACCEPT:
                            self.player_uuid = data.player_uuid
                            self.lobby_uuid = data.lobby_uuid
                            self.sock = ThreadedSocket(sock, self.lock, self)
                            self.sock.start()
                            self.logger.info(
                                'Client joined lobby %s', self.lobby_uuid)
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
        # TODO: Fix seq_num across all files
        payload = Payload(LEAVE, b'', self.lobby_uuid, self.player_uuid, 0)
        self.send(payload.to_bytes())

        # terminate the threaded socket
        self.sock.terminate()
        self.sock.join()

    def send(self, data: bytes):
        """
        Method used to send data to the server.

        :param data: The payload to be sent.
        """
        sock = socket(AF_INET6, SOCK_DGRAM)
        sock.sendto(data, self.remote)
        sock.close()

    def handle_data(self, data: bytes):
        """
        Method used to process data received from the server.

        :param data: The data payload to be handled.
        """
        try:
            incoming = Payload.from_bytes(data)
            # TODO
            # parse the events
            # add it to the queue
            # the UI client / game loop will later process the queue

            return data
        except Exception as e:
            self.logger.warning('Invalid payload received: %s', e)

    @ property
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
