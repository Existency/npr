from logging import Logger
from typing import Optional
from server.server import Server


class ServerCLI:
    """
    This is a cli and wrapper for the server.
    """
    srv: Server
    run: bool
    logger: Logger

    def __init__(self, level: int, id: str):
        """
        Initialize the socket server.
        """
        self.srv = Server(id, level)
        self.run = False
        self.logger = Logger("Server CLI", level=level)
        self.logger.info("Starting CLI.")

    def start(self):
        """
        Start the CLI and socket servers.
        """
        self.run = True
        self.srv.start()  # start the listener server thread

        while self.run:
            # read input from the user
            cmd = input('> ')

            if cmd == 'exit' or cmd == 'quit':
                self.logger.info("Termination requested by cli.")
                self._terminate()

            elif cmd == 'status':
                self._status()

            # if the cmd starts with 'stop' or 'kill'
            elif cmd.startswith('stop') or cmd.startswith('kill'):
                # the rest of the cmd is the lobby uuid
                lobby_uuid = cmd[4:]
                if lobby_uuid == '':
                    self.logger.warning("No lobby uuid provided.")
                    self._help()

                # if the lobby uuid is valid
                if lobby_uuid in self.srv.lobbies:
                    # stop the lobby
                    self.srv.lobbies[lobby_uuid].terminate()
                    self.srv.lobbies[lobby_uuid].join()
                    # remove the lobby from the server
                    del self.srv.lobbies[lobby_uuid]

                    self.logger.info("Lobby %s stopped." % lobby_uuid)

            else:
                self._help()

        self._terminate()

    def _status(self, lobby: Optional[str] = None):
        """
        Prints the status of the server.
        This includes the number of players currently connected and the number of lobbies.
        """
        # get number of lobbies
        print("Number of lobbies: %d" % len(self.srv.lobbies))

        for lob in self.srv.lobbies:
            print("Lobby: %s" % lob.uuid)
            print("Players: %d" % len(lob.conns))

    def _help(self, cmd: Optional[str] = None):
        """
        Prints the help tips for the CLI.

        :param cmd: The command to get help for.
        """
        if cmd is None or cmd == 'help':
            print("""
            Commands:
                help: Prints this help message.
                status: Prints the status of the server.
                exit | stop | quit: Terminates the server.
            """)

        elif cmd == 'status':
            print("""
            Commands:
                status: Prints the status of the server.
                exit | stop | quit: Terminates the server.
            """)

        elif cmd == 'exit' or cmd == 'stop' or cmd == 'quit':
            print("""
            Commands:
                exit | stop | quit: Terminates the server.
            """)

        else:
            print("Unknown command.")
            self._help()

    def terminate(self):
        """
        Terminates the CLI and socket server.
        """
        self.logger.warning("Server shutting down by user request.")
        self.run = False

    def _terminate(self):
        """
        Terminates the CLI and socket server.
        """
        self.logger.info("Terminating CLI.")
        self.srv.terminate()
        self.srv.join()
