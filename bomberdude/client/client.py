import pygame
import pygame_menu

from common.types import DEFAULT_PORT
from .algorithm import Algorithm
from .networking import NetClient
from .game import game_init
from threading import Thread
import time

# pygame goes brr


class Client:

    COLOR_BACKGROUND = (153, 153, 255)
    COLOR_BLACK = (0, 0, 0)
    COLOR_WHITE = (255, 255, 255)
    FPS = 60.0
    MENU_BACKGROUND_COLOR = (102, 102, 153)
    MENU_TITLE_COLOR = (51, 51, 255)
    INFO = None
    TILE_SIZE = None
    WINDOW_SIZE = None
    surface = None
    clock = None
    player_alg = Algorithm.PLAYER
    en1_alg = Algorithm.DIJKSTRA
    en2_alg = Algorithm.DFS
    en3_alg = Algorithm.DIJKSTRA
    show_path = True

    def __init__(self, args, node_path, node_ipv6):
        self.args = args
        self.cli = NetClient((self.args.address, DEFAULT_PORT),
                             node_path=node_path, byte_address=node_ipv6)

    def change_player(self, value, c):
        #global player_alg
        self.player_alg = c

    def run_game(self):
        print("run game")
        self.TILE_SIZE = int(self.INFO.current_h * 0.025)
        game_init(self.show_path, self.player_alg, self.en1_alg,
                  self.en2_alg, self.en3_alg, self.TILE_SIZE, self.cli, self.args)

        self.TILE_SIZE = int(self.INFO.current_h * 0.065)
        self.WINDOW_SIZE = (13 * self.TILE_SIZE, 13 * self.TILE_SIZE)

    def main_background(self):
        self.surface.fill(self.COLOR_BACKGROUND)

    def menu_loop(self):
        pygame.display.init()
        self.INFO = pygame.display.Info()
        self.TILE_SIZE = int(self.INFO.current_h * 0.065)
        self.WINDOW_SIZE = (10 * self.TILE_SIZE, 10 * self.TILE_SIZE)
        self.surface = pygame.display.set_mode(self.WINDOW_SIZE)

        pygame.init()
        self.screen = pygame.display.set_mode((640, 480))
        self.clock = pygame.time.Clock()

        pygame.init()

        pygame.display.set_caption('Bomberman')
        clock = pygame.time.Clock()

        play_menu = pygame_menu.Menu(
            theme=pygame_menu.themes.THEME_DEFAULT,
            height=int(self.WINDOW_SIZE[1] * 0.7),
            width=int(self.WINDOW_SIZE[0] * 0.7),
            onclose=pygame_menu.events.NONE,
            title='Play menu'
        )

        play_options = pygame_menu.Menu(theme=pygame_menu.themes.THEME_DEFAULT,
                                        height=int(self.WINDOW_SIZE[1] * 0.7),
                                        width=int(self.WINDOW_SIZE[0] * 0.7),
                                        title='Options'
                                        )

        play_options.add.selector("Character 1", [("Player", Algorithm.PLAYER), ("DFS", Algorithm.DFS),
                                                  ("DIJKSTRA", Algorithm.DIJKSTRA), ("None", Algorithm.NONE)], onchange=self.change_player)

        play_options.add.button('Back', pygame_menu.events.BACK)
        play_menu.add.button('Start',
                             self.run_game)

        play_menu.add.button('Options', play_options)
        play_menu.add.button('Return  to  main  menu', pygame_menu.events.BACK)

        about_menu_theme = pygame_menu.themes.Theme(
            selection_color=self.COLOR_WHITE,
            widget_font=pygame_menu.font.FONT_BEBAS,
            title_font_size=self.TILE_SIZE,
            title_font_color=self.COLOR_BLACK,
            title_font=pygame_menu.font.FONT_BEBAS,
            widget_font_color=self.COLOR_BLACK,
            widget_font_size=int(self.TILE_SIZE*0.4),
            background_color=self.MENU_BACKGROUND_COLOR,
            title_background_color=self.MENU_TITLE_COLOR,
        )

        about_menu = pygame_menu.Menu(theme=about_menu_theme,
                                      height=int(self.WINDOW_SIZE[1] * 0.7),
                                      width=int(self.WINDOW_SIZE[0] * 0.7),
                                      onclose=pygame_menu.events.NONE,
                                      title='About'
                                      )
        about_menu.add.label("Player_controls: ")
        about_menu.add.label("Movement:_Arrows")
        about_menu.add.label("Plant bomb:_Space")
        about_menu.add.label("Sprite: ")

        about_menu.add.label("https://opengameart.org/content")
        about_menu.add.label("/bomb-party-the-complete-set")

        main_menu = pygame_menu.Menu(
            theme=pygame_menu.themes.THEME_DEFAULT,
            height=int(self.WINDOW_SIZE[1] * 0.6),
            width=int(self.WINDOW_SIZE[0] * 0.6),
            onclose=pygame_menu.events.NONE,
            title='Main menu'
        )

        main_menu.add.button('Play', play_menu)
        main_menu.add.button('About', about_menu)
        main_menu.add.button('Quit', pygame_menu.events.EXIT)

        while True:

            clock.tick(self.FPS)

            self.main_background()

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    exit()

            main_menu.mainloop(self.surface, self.main_background,
                               disable_loop=False, fps_limit=0)
            main_menu.update(events)
            main_menu.draw(self.surface)

            pygame.display.flip()

    def start_game(self):
        self.menu_loop()

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
