from typing import Tuple
from common.payload import ACTIONS, Payload
from common.state import Change, bytes_from_changes 
from common.types import DEFAULT_PORT

class Explosion:

    bomber = None

    def __init__(self, x, y, r,cli):
        self.sourceX = x
        self.sourceY = y
        self.range = r
        self.time = 300
        self.frame = 0
        self.sectors = []
        self.cli = cli
        
    
    def send_pop_box(self,box_sectors):
        list_changes = []
        for box in box_sectors:
            list_changes.append(Change((int(box[1]),int(box[2]),int(box[0])),(int(box[1]),int(box[2]),int(box[0]))))
        
        self.cli.seq_num += 1
        payload = Payload(ACTIONS, bytes_from_changes(list_changes), self.cli.lobby_uuid,
                        self.cli.player_uuid, self.cli.seq_num,self.cli.byte_address,self.cli.byte_address)
        
        self.cli.client_cache.add_entry(
                        (payload.short_destination, DEFAULT_PORT), payload)
        
        #self.cli.unicast(payload.to_bytes())
        
      

    def explode(self, map, bombs, b):

        self.bomber = b.bomber
        self.sectors.extend(b.sectors)
        bombs.remove(b)
        self.bomb_chain(bombs, map)

    def bomb_chain(self, bombs, map):

        for s in self.sectors:
            for x in bombs:
                if x.posX == s[0] and x.posY == s[1]:

                    map[x.posX][x.posY] = 0
                    x.bomber.bomb_limit += 1
                    self.explode(map, bombs, x)

    def clear_sectors(self, map,boxes):
        box_sector = []
        
        for i in self.sectors:
            if map[i[0]][i[1]] == 2:
                t = [i[0],i[1]]
                key = list(boxes.keys())[list(boxes.values()).index(t)]
                
                print('remove block: ',key)
                if key in self.cli.gamestate.boxes:
                    self.cli.gamestate.boxes.pop(key)
                    box_sector.append((key,i[0],i[1]))
                    #self.send_pop_box(key,i[0],i[1])
            map[i[0]][i[1]] = 0
        self.send_pop_box(box_sector)
            

    def update(self, dt):

        self.time = self.time - dt

        if self.time < 100:
            self.frame = 2
        elif self.time < 200:
            self.frame = 1
