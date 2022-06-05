from common.payload import REJOIN, Payload, ACCEPT, REJECT, JOIN
from common.uuid import uuid
from common.core_utils import get_node_ipv6
import logging
from server.connection import Conn
from server.lobby import Lobby
import socket
from threading import Thread
import time


class Server(Thread):
    running: bool
    """Whether the server is running or not."""

    sock: socket.socket
    """The socket used to communicate with the clients."""

    lobbies: list[Lobby]
    """The list of lobbies that are currently running."""

    byte_address: bytes
    """The bytes representation of the server's address"""

    def __init__(self, id: str, port: int, level: int):
        """
        Initialize the socket server.
        """
        Thread.__init__(self)
        self.running = True
        self.lobbies = []
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        self.sock.bind(('', port))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(False)
        self.sock.settimeout(2)

        tmp = get_node_ipv6(id)

        if tmp is not None:
            self.byte_address = tmp

        # Set up logging
        logging.basicConfig(
            level=level, format='%(levelname)s: %(message)s')

        addr = self.sock.getsockname()[0]
        _port = self.sock.getsockname()[1]

        logging.info("Starting server on address \"%s\" \"%d\"", addr, _port)

    def new_lobby(self) -> Lobby:
        """
        Create a new lobby.

        :return: The new lobby.
        """
        # generate a new lobby id
        lobby_id = uuid()

        # get list of lobbies
        lobbies = [lobby.uuid for lobby in self.lobbies]

        # check whether the lobby id is unique,
        # if not, generate a new one and try again
        while lobby_id in lobbies:
            lobby_id = uuid()

        # create a new socket for the lobby
        in_sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        in_sock.bind(('', 0))
        in_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        in_sock.settimeout(2)

        out_sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        out_sock.bind(('', 0))
        out_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        out_sock.settimeout(2)

        # create a new lobby
        lobby = Lobby(lobby_id, in_sock, out_sock, self.byte_address)
        lobby.start()

        # add the lobby to the list of lobbies
        self.lobbies.append(lobby)

        logging.info("Created new lobby: %s on port %d",
                     lobby_id, in_sock.getsockname()[1])

        return lobby

    def get_free_lobby(self) -> Lobby:
        """
        Finds the first lobby that is not full.
        If no free lobby is found, a new lobby is created

        :return: The first lobby that is not full.
        """
        for lobby in self.lobbies:
            if not lobby.is_full:
                logging.debug("Found free lobby: %s", lobby.uuid)
                return lobby

        logging.debug("No free lobby found. Creating new lobby.")
        return self.new_lobby()

    def get_lobby(self, lobby_id: str) -> Lobby:
        """
        Finds the lobby with the given lobby id. If no lobby is found, a new lobby is created.
        :param lobby_id: The id of the lobby to find.
        :return: A lobby with the given id or a new lobby if no lobby with the given id was found.
        """
        for lobby in self.lobbies:
            if lobby.uuid == lobby_id and not lobby.is_full:
                logging.debug("Found lobby: %s", lobby.uuid)
                return lobby

        logging.debug(
            "No lobby found or lobby was full. Creating new lobby.")
        return self.get_free_lobby()

    def _deny(self, conn: Conn, reason: str):
        """
        Creates a response with the given reason and sends it to the client.

        :param conn: The connection to send the response to.
        :param reason: The reason why the connection was denied.
        """
        response = Payload(REJECT, reason.encode('utf-8'), '',
                           conn.uuid, 0, self.byte_address, conn.byte_address)

        self.sock.sendto(response.to_bytes(), conn.address)

    def _accept(self, conn: Conn, lobby: Lobby):
        """
        Creates a response with the given reason and sends it to the client.

        :param conn: The connection to send the response to.
        :param lobby: The lobby the player joined.
        """
        data = lobby.port.to_bytes(2, 'big')
        print(conn.byte_address)

        response = Payload(ACCEPT, data, lobby.uuid, conn.uuid,
                           0, self.byte_address, conn.byte_address)

        self.sock.sendto(response.to_bytes(), conn.address)

    def handle_data(self, data: bytes):
        """
        Handle data received from the socket.

        :param data: The data received from the socket.
        :param addr: The address of the client.
        """
        # check whether the payload is valid
        try:
            inc = Payload.from_bytes(data)

            if inc is None:
                logging.error("Invalid payload received.")
                return

            if inc.type != REJOIN and inc.type != JOIN:
                logging.info("Received invalid payload: %s", inc)
                return

            # if there's a lobby uuid, get the lobby
            if inc.lobby_uuid != '':
                lobby = self.get_lobby(inc.lobby_uuid)

                if lobby.is_full:
                    logging.info("Lobby is full: %s", lobby.uuid)
                    lobby = self.get_free_lobby()
            else:
                lobby = self.get_free_lobby()

            # get a name from the payload's data or 'anonymous' if no name was given
            # TODO: This should be better handled. No sanitization is done here!
            name = inc.data.decode('utf-8') if inc.data != b'' else 'anonymous'

            print(inc.source)

            # create a new connection for the client
            conn = Conn(inc.source, name, time.time())
            # add the connection to the lobby
            lobby.add_player(conn)
            # send the response to the client
            self._accept(conn, lobby)

        except Exception as e:
            logging.error("parsing payload: ", e)

    def run(self):
        """
        Main loop of the server.
        """
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1500)

                logging.debug("Received data from %s: %s", addr, data)
                self.handle_data(data)

            except socket.timeout:
                logging.debug("Socket read timeout, trying again.")
            except BlockingIOError:
                logging.debug("Socket is blocking, this should not happen")
            except Exception as e:
                logging.error("reading from socket: %s", e)

        self._terminate()

    def _terminate(self):
        """
        Terminates the server whenever the thread exits the main loop.
        """
        self.running = False
        logging.info("Closing socket.")
        self.sock.close()

        logging.info("Terminating lobbies.")
        for lobby in self.lobbies:
            lobby.terminate()

        logging.info("Joining threads(lobbies).")
        for lobby in self.lobbies:
            lobby.join()

        logging.info("Terminated. Have a nice day!")

    def terminate(self):
        """
        Called when another entity terminates this server.
        """
        logging.info("Terminating server.")
        self.running = False
