##### TODO:
Server:
 - Game Loop
  - Game State: implement the game state
  - handle_state (server): process game actions by clients

Client:
 - Networking
  - Game Loop:
   - handle_state: process game actions by server
   - handle_state: send game actions to server
 - Pygame
  - Game Loop
   - Display Game State
   - Handle Input
    - Movements / Bombs
    - Pass to Networking.handle_state to send to server.
