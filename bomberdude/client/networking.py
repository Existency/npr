from __future__ import annotations
from dataclasses import dataclass, field
from time import sleep
from typing import Tuple, List
from threading import Thread, Lock
from socket import socket, AF_INET6, SOCK_DGRAM
from logging import Logger
from bomberdude.common.state import Change, parse_payload
from bomberdude.common.payload import REDIRECT, REJECT, Payload, ACCEPT, LEAVE, JOIN


@ dataclass
class NetClient(Thread):
    # class NetClient:
    """
    Networking class used by the client.

    :param remote: The remote address to connect to.
    :param port: The port to connect to.
    """
    remote: Tuple[str, int]
    port: int
    lobby_uuid: str = field(default='')
    player_uuid: str = field(default='')
    sock: ThreadedSocket = field(init=False)  # init'd when joining the server
    inbound_lock: Lock = field(default_factory=Lock)
    queue_inbound: List[Tuple[List[Change], Tuple[str, int]]
                        ] = field(default_factory=list)
    outbound_lock: Lock = field(default_factory=Lock)
    queue_outbound: List[Tuple[Payload, Tuple[str, int]]
                         ] = field(default_factory=list)
    message_lock: Lock = field(default_factory=Lock)
    queue_message: List[Tuple[str, Tuple[str, int]]
                        ] = field(default_factory=list)
    logger: Logger = field(init=False)
    # running: bool = field(init=False, default=False)

    def __post_init__(self):
        self.logger = Logger('NetClient')
        self.logger.info('Client init\'d')

    def join_server(self, lobby_id: str):
        """
        Joins the server, upon joining the ThreadedSocket will start listening.
        """

        payload = Payload(JOIN, b'', lobby_id, '', 0)

        sock = socket(AF_INET6, SOCK_DGRAM)
        sock.bind(('', self.port))
        sock.setblocking(False)
        sock.sendto(payload.to_bytes(), self.remote)

        _try = 0

        while True:
            if _try > 10:
                self.logger.error('Could not join server.')
                raise Exception('Could not join server.')

            try:
                resp, addr = sock.recvfrom(1024)

                if addr == self.remote and resp:
                    data = Payload.from_bytes(resp)

                    if data.type == ACCEPT:
                        self.player_uuid = data.player_uuid
                        self.lobby_uuid = data.lobby_uuid
                        self.sock = ThreadedSocket(
                            self, sock, self.inbound_lock, self.outbound_lock, self.message_lock)
                        self.sock.start()
                        self.logger.info(
                            'Client joined lobby %s', self.lobby_uuid)
                        return True

                    elif data.type == REJECT:
                        self.logger.error('Could not join lobby.')
                        return False
                    else:
                        self.logger.warning('Server returned invalid action')
                        return False

            except Exception as e:
                self.logger.info('Exception: {e}', e)

            _try += 1

    def leave(self):
        """
        Method used to leave the game.
        """
        self.logger.info('Client leaving lobby by user request.')
        # TODO: Fix seq_num across all files
        payload = Payload(LEAVE, b'', self.lobby_uuid, self.player_uuid, 0)
        self.unicast(payload.to_bytes())

        # terminate the threaded socket
        self.sock.terminate()
        self.sock.join()

    # TODO: Check whether this is needed client-side
    def multicast(self, data: bytes):
        """
        Method used to broadcast data using an IPv6 multicast address.

        :param data: The data to be broadcasted.
        """
        pass

    def unicast(self, data: bytes):
        """
        Method used to send data to the server.

        :param data: The payload to be sent.
        """
        sock = socket(AF_INET6, SOCK_DGRAM)
        sock.sendto(data, self.remote)
        sock.close()

    @ property
    def messages(self) -> list:
        """
        Method used to get messages tuples from the queue.
        """
        with self.inbound_lock:
            message: list = self.queue_inbound
            self.queue_inbound = []
            return message

    # def close(self):
    #    self.leave()
    #    self.sock.terminate()
    #    self.sock.join()

    def run(self) -> None:
        """
        Main loop of the networking client.
        """
        self.running = True
        while self.running:
            # TODO: NDN
            # redirect messages from the outbound queue
            #_outbound = []
            #
            # with self.outbound_lock:
            #    _outbound = self.queue_outbound
            #    self.queue_outbound = []

            # A server tick is 1/30th of a second
            sleep(0.0333)

    def terminate(self, reason: str = "Requested by user."):
        """
        Method used to close the client.

        :param reason: The reason for termination.
        """
        self.logger.info('Networking client terminated: {reason}', reason)
        self.leave()
        self.sock.terminate()
        self.sock.join()


@ dataclass
class ThreadedSocket(Thread):
    client: NetClient
    sock: socket
    ilock: Lock
    olock: Lock
    mlock: Lock
    logger: Logger = field(init=False)
    running: bool = field(init=False, default=False)

    def __post__init__(self):
        self.logger = Logger('ThreadedSocket')
        self.logger.info('ThreadedSocket init\'d')

    def handle_data(self, data: bytes, addr: Tuple[str, int]):
        """
        Handles the data received from a remote host.
        This data is converted to a Payload object and then handled.

        As of now this method is used only to handle data received from the server.

        This method will later be used to handle the data received from other peers in the network.

        :param data: The data payload to be handled.
        :param addr: The address of the sender.
        """
        try:

            payload = Payload.from_bytes(data)

            if payload.type == REDIRECT:
                with self.olock:
                    self.client.queue_outbound.append((payload, addr))
                return

            # if the payload is for the server, handle it
            if addr == self.client.remote:
                # Parse the payload and check whether it's an event or not
                # if it's a game event, add it to the queue_inbound
                # if it's not, pass it to the queue_message
                inc = parse_payload(payload)

                # if it's a list of changes, add it to the queue_inbound
                if inc is None:
                    self.logger.info('Received invalid payload')
                    return

                if isinstance(inc, list):
                    with self.ilock:
                        self.client.queue_inbound.append((inc, addr))
                    return

                if isinstance(inc, str):
                    with self.mlock:
                        self.client.queue_message.append((inc, addr))
                    return

                self.logger.warning(
                    'Unhandled payload type. Type: %s', type(inc))

        except Exception as e:
            self.logger.warning('Invalid payload received: {e}', e)

    def run(self):
        """
        Main loop to communicate with the client.
        """
        self.running = True
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)

                Thread(target=self.handle_data, args=(data, addr)).start()
            except Exception as e:
                self.logger.error('Error in ThSocket while recv {e}', e)

        self.terminate("Unexpected condition leading to termination.")

    def terminate(self, reason: str = "Requested by user."):
        """
        Terminates the client

        :param reason: The reason for termination.
        """
        self.logger.info('ThreadedSocket terminated: {reason}', reason)
        self.running = False
        self.sock.close()


# TODO: Implement tests for these.
