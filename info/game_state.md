Game State:
    - The Game State is a 19x19 grid of cells.
    - Each cell has a value.
        - 0x00: Empty
        - 0x01: Crate
        - 0x02: Wall
        - 0x03: Bomb
        - 0x04: Fire
        - 0x05: Player 1
        - 0x06: Player 2
        - 0x07: Player 3
        - 0x08: Player 4

Players: 
    - the spawn point is determined by the lobby
    - can move in any direction.
    - can spawn at most one bomb at a time.
    - can't move through any object.
    - bombs explode after 3 seconds.
    - bombs have a cooldown of 5 seconds.
Bombs:
    - explode after a certain amount of time (3 seconds).
    - explode in a cross pattern (1 block in each direction).
    - if a bomb explodes next to a crate, the crate disappears.
    - if a bomb explodes next to a player, the player dies. 
    - bombs don't destroy walls.
    - bombs don't destroy other bombs.
Fire:
    - fire spreads in a cross pattern (1 block in each direction).
    - fire lasts for a certain amount of time (0.25 second).
Crates:
    - the spawn of crates is determined by the lobby.
    - crates block player movement.

Walls:
    - the spawn of walls is determined by the lobby.
    - walls block player movement.
    - walls block bombs.
    - walls block fire.
    - walls block crates.
    - walls block players.
