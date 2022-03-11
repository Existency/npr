from client.config import PlayerConfig
from transport.base import Connection

import json
import pygame

import os
import sys


# Game state
from typing import Any


class Game:
    player: Any = []
    enemies: Any = []
    bombs: Any = []
    config = None

    def __init__(self):
        self.config = PlayerConfig()

        # Load local config file
        with open(self.config.LOCAL_CONFIG, "r") as f:
            self.local = json.load(f)

        pygame.init()
        self.screen = pygame.display.set_mode(
            (self.local.screen_width, self.local.screen_height))
        pygame.display.set_caption(self.local.title)

        # load the load screen
        self.load_screen = pygame.image.load(
            self.config.RESOURCES_PATH + "loadscreen.png").convert()
        self.load_screen = pygame.transform.scale(
            self.load_screen, (self.local.screen_width, self.local.screen_height))

        # try to connect to the multiplayer server
        self.join_server()

        # main game loop
        while True:
            self.prepare_screen()
            self.play_game()

    def join_server(self):
        """
        Joins a multiplayer server.
        """
        self.client = Connection()
        self.client.connect(self.local.server_ip, self.local.server_port)

    def prepare_screen(self):
        """
        Prepares the screen for the next game loop.
        """
        pass

    def play_game(self):
        """
        Main game loop.
        """

        pass
