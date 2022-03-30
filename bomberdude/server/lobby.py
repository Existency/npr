from __future__ import annotations
from common.payload import ACTIONS, LEAVE, Payload
from .connection import Conn
from logging import Logger
from socket import socket
from threading import Thread, Lock
import time
from typing import Optional, Tuple


class LobbySocket(Thread):
    """
    Background task to receive messages from players,
    processes them and appends them in the Lobby's action_queue_inbound.
    """
    # socket to receive messages from players
    sock: socket
    # Lobby to which the socket belongs
    lobby: Lobby
    # Logger
    logger: Logger
    # game state lock
    game_state_lock: Lock

    def __init__(self, sock: socket, lobby: Lobby, game_state_lock: Lock):
        """
        Initializes the LobbySocket.

        :param sock: Socket to receive messages from players.
        :param lobby: Lobby to which the socket belongs.
        """
        super(LobbySocket, self).__init__()
        self.sock = sock
        self.lobby = lobby
        self.game_state_lock = game_state_lock
        self.running = False
        self.logger = Logger("LobbySocket")
        self.logger.info("Starting LobbySocket on port %d",
                         sock.getsockname()[1])

    def handle_data(self, data: bytes, addr: Tuple[str, int]):
        """
        Handles a message received from the socket.

        :param data: The message received from the socket.
        :param addr: The address that sent the message.
        """

        # check whether the message comes from a valid player
        player = self.lobby.get_player(addr)

        if player is None:
            self.logger.info("Received message from invalid player %s", addr)
            return  # TODO: add a block mechanism to prevent spamming the server

        msg = Payload.from_bytes(data)

        # if the message seq_num is older than the conn's seq_num, ignore it
        if msg.seq_num < player.seq_num:
            self.logger.info("Received message with old seq_num %d from %s",
                             msg.seq_num, addr)
            return

        if msg.type == ACTIONS:
            # add the message to the lobby's action_queue_inbound
            self.lobby.action_queue_inbound.append(msg.data)
        elif msg.type == LEAVE:
            # remove the player from the lobby
            self.lobby.remove_player(player)
        else:
            self.logger.info("Received invalid payload: %s", msg)
            return

    @property
    def port(self) -> int:
        """
        Gets the port of the lobby.
        """
        return self.sock.getsockname()[1]

    @property
    def ip(self) -> str:
        """
        Gets the IP of the lobby.
        """
        return self.sock.getsockname()[0]

    @property
    def addr(self) -> Tuple[str, int]:
        """
        Gets the address of the lobby.
        """
        return self.sock.getsockname()

    def run(self):
        """
        The main loop for the LobbySocket.

        New messages are received from the socket and processed.
        """
        self.running = True
        while self.running:
            # receive message from socket
            data, addr = self.sock.recvfrom(1024)
            # spawn a new thread to handle the message
            Thread(target=self.handle_data, args=(data, addr)).start()

    def stop(self):
        """
        Stops the LobbySocket.
        """
        self.running = False
        self.sock.close()
        self.logger.info("Stopped LobbySocket on port %d",
                         self.sock.getsockname()[1])


class Lobby(Thread):
    """
    A Lobby is a thread that implements the basic game logic.
    A Lobby is a thread that is responsible for:
        - Accepting/Rejecting connections
        - Game logic
        - Handling incoming data
    """
    # max number of players allowed in the lobby
    capacity: int
    # list of players currently present in the lobby
    conns: list
    # list of actions that are yet to be handled
    action_queue_inbound: list
    # list of actions that are yet to be sent
    action_queue_outbound: list
    # current state of the game
    game_state: list
    # lock used to protect game state from multiple thread access
    game_state_lock: Lock
    # flag to indicate whether the lobby has a running game
    in_game: bool
    # logger used to log messages to the console
    logger: Logger
    # flag to indicate whether the lobby is running
    running: bool
    # socket used to receive data from clients
    sock: LobbySocket
    # lobby uuid
    uuid: str

    def __init__(self, uuid: str, sock: socket, capacity: int = 4):
        super(Lobby, self).__init__()
        self.capacity = capacity
        self.conns = []
        self.action_queue_inbound = []
        self.action_queue_outbound = []
        self.game_state = []
        self.game_state_lock = Lock()
        self.in_game = False
        self.logger = Logger('Lobby')
        self.running = False
        self.uuid = uuid
        self.sock = LobbySocket(sock, self, self.game_state_lock)  # TODO
        self.logger.info('Lobby init\'d')

    def add_player(self, conn: Conn) -> bool:
        """
        Adds a conn to the lobby.

        :param conn: The conn to be added.
        """
        if self.is_full:
            self.logger.info(
                'Lobby is fully, cannot add conn, {conn}')
            return False

        # check whether the connection already exists
        for c in self.conns:
            if c.address == conn.address:
                self.logger.info(
                    'Connection already exists, {conn}')
                return False

        self.conns.append(conn)
        self.logger.info('Added conn to lobby, {conn}')
        return True

    def get_player(self, addr: Tuple[str, int]) -> Optional[Conn]:
        """
        Gets a conn from the lobby.

        :param addr: The address of the conn to be retrieved.
        """
        for c in self.conns:
            if c.address == addr:
                return c
        return None

    def remove_player(self, conn) -> bool:
        """
        Removes a conn from the lobby.

        :param conn: The conn to be removed.
        """
        if conn not in self.conns:
            self.logger.info(
                'Connection not found, {conn}')
            return False

        self.conns.remove(conn)
        self.logger.info('Removed conn from lobby, {conn}')
        return True

    @ property
    def is_full(self) -> bool:
        """
        Returns True if the lobby is full.
        """
        if len(self.conns) == self.capacity:
            return True
        else:
            return False

    @ property
    def is_empty(self) -> bool:
        """
        Returns True if the lobby is empty.
        """
        if len(self.conns) == 0:
            return True
        else:
            return False

    @property
    def address(self) -> Tuple[str, int]:
        """
        Fetches the ip address of the lobby.

        Returns:
            The address of the lobby.
        """
        return self.sock.addr

    @property
    def port(self) -> int:
        """
        Fetches the port of the lobby.
        """
        return self.sock.port

    @property
    def ip(self) -> str:
        """
        Fetches the ip address of the lobby.
        """
        return self.sock.ip

    # TODO: Find out how ipv6 will affect this
    def unicast(self, data: bytes, conn: Conn):
        """
        Sends data to a conn in the lobby.

        :param data: The data to be sent.
        :param conn: The conn to be sent to.
        """
        if conn not in self.conns:
            raise ValueError('Connection not found')

        conn.send(data)

    # TODO: Find out how ipv6 will affect this
    def multicast(self, data: bytes, blacklist: Optional[Conn] = None):
        """
        Sends data to all conns in the lobby.

        :param data: The data to be sent.
        """
        # get all conns excluding the blacklist
        conns = [c for c in self.conns if c != blacklist]

        # send data to all conns
        for c in conns:
            c.send(data)

    def _apply_state_change(self, state: list) -> bool:
        """
        Applies a state change to the game state.

        :param state: The state change to be applied.
        :return: True if the state change was applied successfully.
        """
        # TODO: implement state change
        return True

    def _handle_game_action(self, data: bytes, conn: Conn):
        """
        Handles game actions received from a conn.

        :param data: The data received.
        :param conn: The conn that sent the data.
        """

        if not self.in_game:
            self.logger.error('Game not in progress, {conn}')
            return

        # send an ACK to the client and multicast the action to all other clients
        # multicast = {
        #    'action': 'state',
        #    'state': self.game_state
        # }
        #
        #
        #
        # unicast = {
        #    'action': 'ack'
        # }
        #
        # self.multicast(json.dumps(multicast).encode('utf-8'))
        #self.unicast(json.dumps(unicast).encode('utf-8'), conn)

    def run(self):
        """
        Main game server loop.
        """
        self.running = True
        while self.running:
            # TODO: Handle game actions
            # TODO: Handle leave lobby
            # check whether we have enough players to start the game
            while not self.is_full:
                self.logger.info('Waiting for more players')
                # Wait for more players to join
                time.sleep(0.005)  # TODO: Change this to a better solution
                pass

            self.in_game = True
            self.logger.info('Game starting soon™')
            while self.in_game:
                pass

    def terminate(self):
        """
        Terminates the lobby.
        """
        self.logger.info('Terminating lobby')
        self.running = False
        self.sock.stop()
        self.sock.join()

# TODO: Implement test suite
