from logging import Logger
from optparse import Option
from typing import Optional, Tuple
from .lobby import Lobby
from .connection import Conn
from threading import Thread
import json
import socket
import uuid


class Server(Thread):
    port: int
    running: bool
    sock: socket.socket
    logger: Logger
    lobbies: list[Lobby]

    def __init__(self, port: int):
        """
        Initialize the socket server.
        """
        Thread.__init__(self)
        self.port = port
        self.running = True
        self.lobbies = []
        self.logger = Logger("Server")
        self.logger.info("Starting server on port %d", self.port)

    def new_lobby(self) -> Lobby:
        """
        Create a new lobby.

        Returns:
            The id of the new lobby.
        """
        # generate a new lobby id
        lobby_id = str(uuid.uuid4())

        # get list of lobbies
        lobbies = [lobby.id for lobby in self.lobbies]

        # check whether the lobby id is unique,
        # if not, generate a new one and try again
        while lobby_id in lobbies:
            lobby_id = str(uuid.uuid4())

        # create a new socket for the lobby
        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        sock.bind(('', 0))

        # create a new lobby
        lobby = Lobby(lobby_id, sock)
        lobby.start()

        # add the lobby to the list of lobbies
        self.lobbies.append(lobby)

        return lobby

    def get_free_lobby(self) -> Lobby:
        """
        Finds the first lobby that is not full.
        If no free lobby is found, a new lobby is created

        Returns:
            The id of the free lobby.
        """
        for lobby in self.lobbies:
            if not lobby.is_full:
                return lobby

        return self.new_lobby()

    def get_lobby(self, lobby_id: str) -> Lobby:
        """
        Finds the lobby with the given lobby id.
        """
        for lobby in self.lobbies:
            if lobby.id == lobby_id:
                return lobby

        return self.new_lobby()

    def _deny(self, conn: Conn, reason: str):
        """
        Creates a response with the given reason and sends it to the client.

        Args:
            conn: The connection to send the response to.
            reason: The reason why the connection was denied.
        """
        response = {
            'action': 'deny',
            'name': conn.name,
            'reason': reason,
        }

        self.sock.sendto(json.dumps(response).encode('utf-8'), conn.address)

    def _accept(self, conn: Conn, lobby: Lobby):
        """
        Creates a response with the given reason and sends it to the client.

        Args:
            conn: The connection to send the response to.
            reason: The reason why the connection was denied.
        """
        response = {
            'action': 'accept',
            'lobby': lobby.id,
            'uuid': conn.uuid,
            'name': conn.name,
            'port': lobby.address[1],
            'reason': '',
        }

        self.sock.sendto(json.dumps(response).encode('utf-8'), conn.address)

    def handle_data(self, data: bytes, addr: Tuple[str, int]):
        """
        Handle data received from the socket.
        """
        # check whether the payload is valid
        incoming: dict = {}
        try:
            incomming = json.loads(data.decode('utf-8'))
            # {
            #     "action": "join",
            #     "lobby": "",
            #     "name": "TheLegend27",
            # }

            if incoming['action'] != 'join':
                self.logger.warning("Invalid action: %s", incoming['action'])
                return  # Invalid action

            # check whether the lobby exists

            if len(incomming['lobby']) != 0:
                lobby = self.get_lobby(incoming['lobby'])
                if lobby.is_full:
                    self.logger.info("Lobby requested is full")
                    lobby = self.get_free_lobby()

            else:
                lobby = self.get_free_lobby()

            # create a new connection
            conn = Conn(incoming['name'], addr)
            # add the player to the lobby
            lobby.add_player(conn)

            self._accept(conn, lobby)

        except json.JSONDecodeError:
            self.logger.info("Invalid JSON data received")

    def run(self):
        """
        Main loop of the socket server.
        """
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.sock.bind(('', self.port))
        self.sock.setblocking(False)
        self.sock.settimeout(2)

        while self.running:
            data = b''

            try:
                data, addr = self.sock.recvfrom(1024)
            except socket.timeout:
                self.logger.debug("Socket read timeout")
                continue

            self.logger.debug("Received data from %s: %s", addr, data)
            self.handle_data(data, addr)

        self.terminate()

    def terminate(self):
        """
        Terminate the socket server.
        """
        self.logger.info("Terminating server.")
        self.running = False
        self.logger.info("Closing socket.")
        self.sock.close()

        self.logger.info("Terminating lobbies.")
        for lobby in self.lobbies:
            lobby.terminate()

        self.logger.info("Joining threads(lobbies).")
        for lobby in self.lobbies:
            lobby.join()

        self.logger.info("Terminated. Have a nice day!")
