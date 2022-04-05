from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from common.state import Change, GameState, parse_payload
from common.payload import ACTIONS, KALIVE, STATE, Payload, ACCEPT, LEAVE, JOIN, REDIRECT, REJECT, int_to_type
from dataclasses import dataclass, field
import logging
import time
from typing import Tuple, List
from threading import Thread, Lock
from socket import socket, AF_INET6, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR
import json


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
    level: int = field(default=logging.INFO)
    slock: Lock = field(init=False, default_factory=Lock)
    gamestate: GameState = field(init=False)
    lobby_uuid: str = field(default='')
    player_uuid: str = field(default='')
    # sock: ThreadedSocket = field(init=False)  # init'd when joining the server
    sock: socket = field(init=False)
    inbound_lock: Lock = field(default_factory=Lock)
    queue_inbound: List[Change] = field(
        default_factory=list)
    outbound_lock: Lock = field(default_factory=Lock)
    queue_outbound: List[Tuple[Payload, Tuple[str, int]]
                         ] = field(default_factory=list)
    message_lock: Lock = field(default_factory=Lock)
    queue_message: List[Tuple[bytes,
                              Tuple[str, int]]] = field(default_factory=list)
    running: bool = field(init=False, default=False)
    player_id: int = field(init=False, default=0)
    started: bool = field(init=False, default=False)
    last_kalive: float = field(init=False, default=0.0)
    lobby_port: int = field(init=False)

    def __hash__(self) -> int:
        return super().__hash__()

    def __post_init__(self):
        super(NetClient, self).__init__()
        self.gamestate = GameState(self.slock, {})
        logging.basicConfig(
            level=self.level, format='%(levelname)s: %(message)s')

        logging.info('Client init\'d')

    @ property
    def messages(self) -> list:
        """
        Method used to get messages tuples from the queue.
        """
        with self.inbound_lock:
            message: list = self.queue_inbound
            self.queue_inbound = []
            return message

    def join_server(self, lobby_id: str):
        """
        Joins the server, upon joining the ThreadedSocket will start listening.
        """

        payload = Payload(JOIN, b'', lobby_id, '', 0)

        sock = socket(AF_INET6, SOCK_DGRAM)
        sock.bind(('', self.port))
        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        # sock.setblocking(True)
        sock.sendto(payload.to_bytes(), self.remote)

        _try = 0

        while True:
            try:
                resp, addr = sock.recvfrom(1024)

                if len(resp) < 17:
                    # ignore these packets
                    _try -= 1
                    continue

                logging.info("Join: Received response on socket.")

                # why the hell do you fail?!?!
                data = Payload.from_bytes(resp)
                # se isto continuar sem funcionar é porque struct (module) não funciona como penso

                if addr[0] == self.remote[0] and addr[1] == self.remote[1]:
                    if data.type == ACCEPT:
                        self.player_uuid = data.player_uuid
                        self.lobby_uuid = data.lobby_uuid
                        # decode the payload's data.
                        # It's supposed to be an int, 2 bytes, representing the port to which we must connect.
                        self.lobby_port = int.from_bytes(
                            data.data, byteorder='big')
                        logging.info('New lobby port: %d', self.lobby_port)
                        self.sock = sock
                        logging.info('Client joined lobby %s', self.lobby_uuid)
                        self.last_kalive = time.time()  # set kalive to now
                        return True

                    elif data.type == REJECT:
                        logging.error('Could not join lobby.')
                        return False
                    else:
                        logging.warning('Server returned invalid action')
                        return False

            except Exception as e:
                logging.error('Exception: %s', e.__str__())

            _try += 1

            if _try > 10:
                logging.error('Could not join server.')
                exit(1)

            time.sleep(0.3)

    # TODO: This will be needed later on
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

    def _kalive(self):
        """
        Constantly updates the kalive.
        """
        while self.running:
            payload = Payload(KALIVE, b'', self.lobby_uuid,
                              self.player_uuid, 0)
            self.unicast(payload.to_bytes())
            time.sleep(1)

    def _handle_state(self):
        """
        Method shouldn't be called directly from outside the class.

        This method is used to handle the inbound queue.
        """
        self.started = False
        while self.running:
            while not self.started:
                # Wait until server sends us a STATE message with our ID
                time.sleep(0.1)

            # reset for next game
            self.started = False
            self.in_game = True
            while self.in_game:
                _incoming_changes = []

                with self.slock:
                    _incoming_changes = self.queue_inbound
                    self.queue_inbound = []

                for change in _incoming_changes:
                    self.gamestate._apply_change(change)

                time.sleep(0.03)

    def _broadcast_kalive(self):
        """
        Method shouldn't be called directly from outside the class.

        This method is used to broadcast the kalive to the server.
        """
        while self.running:
            # check whether last kalive from server was more than 5 seconds ago
            if time.time() - self.last_kalive > 5:
                logging.warning('Server not responding...')

            payload = Payload(KALIVE, b'', self.lobby_uuid,
                              self.player_uuid, 0)

            # add the payload to the queue_outbound
            with self.outbound_lock:
                self.queue_outbound.append((payload, self.remote))
            time.sleep(1)

    def _handle_output(self):
        """
        Method shouldn't be called directly from outside the class.

        This method is used to handle the outbound queue.
        """
        while self.running:
            actions = []

            with self.outbound_lock:
                actions = self.queue_outbound
                self.queue_outbound = []

            for action in actions:
                self.unicast(action[0].to_bytes())

            time.sleep(0.03)

    def _handle_input(self):
        """
        Method shouldn't be called directly from outside the class.

        Handles the data received from a remote host.
        This data is converted to a Payload object and then handled.
        """
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)

                if len(data) < 17:
                    continue

                payload = Payload.from_bytes(data)

                if payload.type == REDIRECT:
                    with self.outbound_lock:
                        self.queue_outbound.append((payload, addr))
                    return

                # if the payload is for the server, handle it
                if addr[0] == self.remote[0] and addr[1] == self.lobby_port:
                    # Parse the payload and check whether it's an event or not
                    # if it's a game event, add it to the queue_inbound
                    # if it's not, pass it to the queue_message
                    if payload.type == KALIVE:
                        logging.debug('Received KALIVE.')
                        self.last_kalive = time.time()

                    elif payload.type == ACTIONS:
                        inc = parse_payload(payload)

                        if inc is not None:
                            with self.inbound_lock:
                                self.queue_inbound.extend(inc)

                    elif payload.type == STATE and self.started == False:
                        # update the client's state and set the started flag to true

                        state = json.loads(payload.data.decode('utf-8'))
                        if state['uuid'] == self.player_uuid:
                            self.started = True
                            self.player_id = state.player_id
            except Exception as e:
                logging.warning('Invalid payload received: %s',
                                e.__str__())

        self.terminate("Unexpected condition leading to termination.")

        pass

    def run(self):
        """
        Main loop of the networking client.
        """

        self.running = True
        with ThreadPoolExecutor(max_workers=4) as executor:
            executor.submit(self._handle_input)
            executor.submit(self._handle_state)
            executor.submit(self._handle_output)
            executor.submit(self._broadcast_kalive)
            executor.shutdown(wait=True)

    def leave(self):
        """
        Method used to leave the game.
        """
        logging.info('Client leaving lobby by user request.')
        # TODO: Fix seq_num across all files
        payload = Payload(LEAVE, b'', self.lobby_uuid, self.player_uuid, 0)
        self.unicast(payload.to_bytes())
        # terminate the threaded socket

    def terminate(self, reason: str = "Requested by user."):
        """
        Method used to close the client.

        :param reason: The reason for termination.
        """
        logging.info('Networking client terminated: {reason}', reason)
        self.running = False
        self.in_game = False
        self.leave()


@ dataclass
class ThreadedSocket(Thread):
    client: NetClient
    sock: socket
    ilock: Lock
    olock: Lock
    mlock: Lock
    level: int = field(default=logging.INFO)
    running: bool = field(init=False, default=False)

    def __hash__(self) -> int:
        return super().__hash__()

    def __post__init__(self):
        super(ThreadedSocket, self).__init__()
        logging.basicConfig(
            level=self.level, format='%(levelname)s: %(message)s')

        logging.info('ThreadedSocket init\'d')

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
                if payload.type == ACTIONS:
                    inc = parse_payload(payload)

                    if inc is not None:
                        with self.ilock:
                            self.client.queue_inbound.extend(inc)

                elif payload.type == STATE and self.client.started == False:
                    # update the client's state and set the started flag to true
                    state = json.loads(payload.data.decode('utf-8'))
                    if state.uuid == self.client.player_uuid:
                        self.client.started = True
                        self.client.player_id = state.player_id

        except Exception as e:
            logging.warning('Invalid payload received: {e}', e)

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
                logging.error('Error in ThSocket while recv {e}', e)

        self.terminate("Unexpected condition leading to termination.")

    def terminate(self, reason: str = "Requested by user."):
        """
        Terminates the client

        :param reason: The reason for termination.
        """
        logging.info('ThreadedSocket terminated: {reason}', reason)
        self.running = False
        self.sock.close()


# TODO: Implement tests for these.
