import json
from socket import socket
from typing import Optional, Tuple

from pyrsistent import T
from .connection import Conn
from threading import Thread, Lock
from logging import Logger


# TODO: implement multithreading for lobby
class Lobby(Thread):
    """
    A Lobby is a thread that implements the basic game logic.
    A Lobby is a thread that is responsible for:
        - Accepting/Rejecting connections
        - Game logic
        - Handling incoming data
    """
    id: str
    # list of players currently present in the lobby
    conns: list
    # max number of players allowed in the lobby
    capacity: int
    logger: Logger
    sock: socket
    running: bool
    in_game: bool
    data_lock: Lock

    def __init__(self, id: str, sock: socket, capacity: int = 4):
        super(Lobby, self).__init__()
        self.capacity = capacity
        self.conns = []
        self.sock = sock
        self.id = id
        self.logger = Logger('Lobby')
        self.logger.info('Lobby init\'d')
        self.running = False
        self.in_game = False
        self.data_lock = Lock()

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

    def rm_player(self, conn) -> bool:
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
        return self.sock.getsockname()

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

    def _handle_game_action(self, data: bytes, conn: Conn):
        """
        Handles game actions.

        :param data: The data received.
        :param conn: The conn that sent the data.
        """
        pass

    def handle_data(self, data: bytes, conn: Conn):
        """
        Handles data received from a conn.

        :param data: The data received.
        :param conn: The conn that sent the data.
        """
        # Payload types that are handled by the lobby (from client):
        #   Game Action
        #   Leave Lobby

        # check whether the payload has a valid action
        incoming = json.loads(data.decode('utf-8'))

        if 'action' not in incoming:
            self.logger.info('Invalid payload, {data}')
            return

        action = incoming['action']

        if action == 'leave':
            self.logger.info('{conn} has left the lobby.')
            self.rm_player(conn)
        elif action == 'game':
            self.logger.info('Game action received from {conn}.')
            self._handle_game_action(data, conn)
        else:
            self.logger.info('Invalid action {action} from {conn}.')

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
                pass

            self.in_game = True
            self.logger.info('Game starting soon™')
            while self.in_game:
                # read incoming data
                data, addr = self.sock.recvfrom(1024)

                # find whether the data is from a known conn
                for c in self.conns:
                    if c.address == addr:
                        # spawn a thread to handle the data
                        Thread(target=self.handle_data, args=(data, c)).start()
                        break

                #

                # send data to all conns

    def terminate(self):
        """
        Terminates the lobby.
        """
        self.logger.info('Terminating lobby')
        self.running = False
        self.sock.close()
