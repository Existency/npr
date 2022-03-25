from logging import Logger
from .server import Server
import argparse


class ServerCLI:
    """
    This is a cli and wrapper for the server.
    """
    srv: Server
    run: bool
    logger: Logger

    def __init__(self, port: int):
        """
        Initialize the socket server.
        """
        self.srv = Server(port)
        self.run = False
        self.logger = Logger("Server CLI")
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

            if cmd == 'exit' or cmd == 'stop' or cmd == 'quit':
                self.logger.info("Termination requested by cli.")
                self._terminate()

            elif cmd == 'help':
                self._help()

            elif cmd == 'status':
                self._status()

        self._terminate()

    def _status(self):
        """
        Prints the status of the server.
        This includes the number of players currently connected and the number of lobbies.
        """
        # get number of lobbies
        num_lobbies = len(self.srv.lobbies)

    def _help(self):
        pass

    def _terminate(self):
        """
        Terminates the CLI and socket server.
        """
        self.logger.info("Server shutting down.")
        self.run = False
        self.srv.terminate()
        self.srv.join()


if __name__ == '__main__':
    """
    Start the bomberdude server.
    """
    parser = argparse.ArgumentParser(description='Bomberdude server.')
    parser.add_argument('-p', '--port', type=int, default=8080,)
    args = parser.parse_args()

    srv = ServerCLI(args.port)
    srv.start()
