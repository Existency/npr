
class PlayerConfig(object):
    """
    Local config
    """
    # tiles
    TILE_EMPTY = 0
    TILE_WALL = 1
    TILE_BOX = 2
    TILE_PLAYER = 3
    TILE_ENEMY = 4
    TILE_BOMB = 5
    TILE_EXPLOSION = 6
    # resource locations
    RESOURCES_PATH = "resources/"
    SPRITES_PATH = "resources/sprites/"
    # game settings
    LOCAL_CONFIG = "config.json"
    # game constants
    GRID_LAYOUT = [[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                   [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                   [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
                   [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                   [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
                   [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                   [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
                   [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                   [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
                   [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                   [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
                   [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
                   [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]]
