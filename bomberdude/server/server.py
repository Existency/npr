from server.connection import Conn
from server.lobby import Lobby
from common.payload import Payload, ACCEPT, REJECT, JOIN
from common.uuid import uuid
import time
import socket
from threading import Thread
from typing import Tuple


class Server(Thread):
    running: bool
    sock: socket.socket
    lobbies: list[Lobby]

    def __init__(self, port: int, level: int):
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
        print("Info: Starting server on address ",
              self.sock.getsockname())

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
        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        sock.bind(('', 0))

        # create a new lobby
        lobby = Lobby(lobby_id, sock)
        lobby.start()

        # add the lobby to the list of lobbies
        self.lobbies.append(lobby)

        print("Info: Created new lobby: %s on port %d",
              lobby_id, sock.getsockname()[1])

        return lobby

    def get_free_lobby(self) -> Lobby:
        """
        Finds the first lobby that is not full.
        If no free lobby is found, a new lobby is created

        :return: The first lobby that is not full.
        """
        for lobby in self.lobbies:
            if not lobby.is_full:
                print("Debug: Found free lobby: %s", lobby.uuid)
                return lobby

        print("Debug: No free lobby found. Creating new lobby.")
        return self.new_lobby()

    def get_lobby(self, lobby_id: str) -> Lobby:
        """
        Finds the lobby with the given lobby id. If no lobby is found, a new lobby is created.

        :param lobby_id: The id of the lobby to find.
        :return: A lobby with the given id or a new lobby if no lobby with the given id was found.
        """
        for lobby in self.lobbies:
            if lobby.uuid == lobby_id and not lobby.is_full:
                print("Debug: Found lobby: %s", lobby.uuid)
                return lobby

        print("Debug: No lobby found or lobby was full. Creating new lobby.")
        return self.new_lobby()

    def _deny(self, conn: Conn, reason: str):
        """
        Creates a response with the given reason and sends it to the client.

        :param conn: The connection to send the response to.
        :param reason: The reason why the connection was denied.
        """
        rsp = Payload(REJECT, reason.encode('utf-8'), '', conn.uuid, 0)

        self.sock.sendto(rsp.to_bytes(), conn.address)

    def _accept(self, conn: Conn, lobby: Lobby):
        """
        Creates a response with the given reason and sends it to the client.

        :param conn: The connection to send the response to.
        :param lobby: The lobby the player joined.
        """
        data = lobby.port.to_bytes(2, 'big')
        # response to be sent to client, containing the lobby port in the data field
        rsp = Payload(
            ACCEPT, data, lobby.uuid, conn.uuid, 0)

        self.sock.sendto(rsp.to_bytes(), conn.address)

    def handle_data(self, data: bytes, addr: Tuple[str, int]):
        """
        Handle data received from the socket.

        :param data: The data received from the socket.
        :param addr: The address of the client.
        """
        # check whether the payload is valid
        try:
            inc = Payload.from_bytes(data)

            if inc.type != JOIN:
                print("Info: Received invalid payload: %s", inc)
                return

            # if there's a lobby uuid, get the lobby
            if inc.lobby_uuid != '':
                lobby = self.get_lobby(inc.lobby_uuid)

                if lobby.is_full:
                    print("Info: Lobby is full: %s", lobby.uuid)
                    lobby = self.get_free_lobby()

            else:
                lobby = self.get_free_lobby()

            # get a name from the payload's data or 'anonymous' if no name was given
            # TODO: This should be better handled. No sanitization is done here!
            name = inc.data.decode('utf-8') if inc.data != b'' else 'anonymous'

            # create a new connection for the client
            conn = Conn(addr, name, int(time.time()))
            # add the connection to the lobby
            lobby.add_player(conn)
            # send the response to the client
            self._accept(conn, lobby)

        except Exception as e:
            print("Error: parsing payload: %s", e)

    def run(self):
        """
        Main loop of the server.
        """
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)

                print("Debug: Received data from %s: %s", addr, data)
                self.handle_data(data, addr)

            except socket.timeout:
                print("Debug: Socket read timeout, trying again.")
            except BlockingIOError:
                print("Debug: Socket is blocking, this should not happen")
            except Exception as e:
                print("Error: reading from socket: %s", e)

        self._terminate()

    def _terminate(self):
        """
        Terminates the server whenever the thread exits the main loop.
        """
        self.running = False
        print("Info: Closing socket.")
        self.sock.close()

        print("Info: Terminating lobbies.")
        for lobby in self.lobbies:
            lobby.terminate()

        print("Info: Joining threads(lobbies).")
        for lobby in self.lobbies:
            lobby.join()

        print("Info: Terminated. Have a nice day!")

    def terminate(self):
        """
        Called when another entity terminates this server.
        """
        print("Info: Terminating server.")
        self.running = False
