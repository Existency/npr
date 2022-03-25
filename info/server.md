Server CLI -> _Server(Thread) -> List[Lobby(Thread)]

Server CLI:
 - command line interface for the server

_Server(Thread):
 - server responsible for managing the lobby/lob
 - accepts new clients
    - when a client connects, it is added to a free lobby
    - if no lobby is available, a new lobby is created
    - when a client joins a lobby, the lobby's ip:port is sent to the client
 - disconnections aren't handled by _Server, but by Lobby


Lobby(Thread)
 - Each lobby creates a socket and listens to clients' packets
 - responsible for the implementation of the game's logic
 - starts a game when the number of players is max_capacity
 - the game doesn't stop until it's over or only one player is left
 - the lobby is responsible for the communication between the players



# TODO:
 - learn whatever we need to do with DTN
 - maybe a blacklist for undesirable clients? (spam/black holes)


Payload actions:

# Client trying to join the server

Client -> Server
   
   {
      "action": "join",
      "lobby": lobby_id | '',
      "name": "TheLegend27",
   }

Server -> Client (accept)
   
   {
      "action": "accept",
      "lobby": "the lobby's uuid",
      "uuid": "the player's uuid",
      "name": "TheLegend27",
      "port": Lobby's port,
   }

Server -> Client (deny)
   
   {
      "action": "deny",
      "name": "TheLegend27",
      "reason": "",
   }

# Client communicating with the game server

Client -> Server
   
   {
      "action": "game",
      "lobby": "lobbyid",
      "uuid": "playerid",
      "seq_num": seq_num,
      "game_actions": ["action1", "action2", ...]
   }

Server -> Client

   {
      "action": "ack",
      "seq_num": seq_num
   }

Server -> Client(Others)

   {
      "action": "game",
      "lobby": "lobbyid",
      "uuid": "playerid",
      "seq_num": seq_num,
      "game_actions": ["action1", "action2", ...]
   }

# Client leaving the server

Client -> Server
   - Fallible
   
   {
      "action": "leave",
      "lobby": "lobbyid",
      "uuid": "playerid",
      "seq_num": seq_num,
   }

Server -> Client
   - Fallible

   {
      "action": "ack",
      "seq_num": seq_num
   }

Server -> Client(Others)
   - Must be acked by the client

   {
      "action": "leave",
      "lobby": "lobbyid",
      "uuid": "playerid",
      "seq_num": seq_num,
      "game_actions": ["Player left, 0x05..0x08"]
   }

Client(Others) -> Server
   - Must ack this seq_num in particular

   {
      "action": "ack",
      "seq_num": seq_num
   }

