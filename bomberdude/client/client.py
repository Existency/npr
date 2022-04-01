from .networking import NetClient
import pygame

# pygame goes brr


class Client:
    def __init__(self, host, port):
        self.net = NetClient(host, port)

    def run(self):
        # init pygame
        pygame.init()
        self.screen = pygame.display.set_mode((640, 480))
        self.clock = pygame.time.Clock()

        # main loop
        while True:
            # handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.net.terminate()
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.net.terminate()
                        return

            # update
            # self.net.update()

            # draw
            self.screen.fill((0, 0, 0))
            # self.net.draw(self.screen)
            pygame.display.flip()

            # sleep
            self.clock.tick(60)

    def stop(self):
        self.net.terminate()
        pygame.quit()

    def send(self, data):
        self.net.unicast(data)

    def messages(self) -> list:
        """
        retrieves all messages from the NetClient queue
        """
        return self.net.messages
