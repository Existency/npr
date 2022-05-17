from matplotlib.pyplot import grid
import pygame
import random
from .bomb import Bomb
from .node import Node
from .algorithm import Algorithm
from common.payload import ACTIONS, KALIVE, REJOIN, STATE, Payload, ACCEPT, LEAVE, JOIN, REDIRECT, REJECT
from common.state import Change
from typing import Tuple, List
from threading import Lock
import math, time


class Enemy:

    dire = [[1, 0, 1], [0, 1, 0], [-1, 0, 3], [0, -1, 2]]

    def __init__(self, x, y, alg,cli,id):
        self.cli = cli
        self.life = True
        self.path = []
        self.movement_path = []
        self.posX = x * 4
        self.posY = y * 4
        self.direction = 0
        self.frame = 0
        self.animation = []
        self.range = 3
        self.bomb_limit = 1
        self.plant = False
        self.algorithm = alg
        self.lock = Lock()
        self.id = id

    def sendAction(self,action,x,y):
        move_x,move_y = self.posX,self.posY
        
        tile_id = None    
        match action:
            case 'move' : tile_id = self.cli.player_id + 9
            case 'bomb': tile_id = 2
        

        data = Change((int(x/4),int(y/4),self.cli.player_id+9),(int(move_x/4),int(move_y/4),tile_id))
        self.cli.seq_num += 1
        payload = Payload(ACTIONS, data.to_bytes(), self.cli.lobby_uuid,
                        self.cli.player_uuid, self.cli.seq_num)
        
        self.cli.unicast(payload.to_bytes())

    def move(self, map, bombs, explosions, enemy):

        if self.direction == 0:
            
            self.posY += 1
        elif self.direction == 1:
            
            self.posX += 1
        elif self.direction == 2:
            
            self.posY -= 1
        elif self.direction == 3:
            
            self.posX -= 1

        if self.posX % 4 == 0 and self.posY % 4 == 0:
            self.movement_path.pop(0)
            self.path.pop(0)
            if len(self.path) > 1:
                grid = self.create_grid(map, bombs, explosions, enemy)
                next = self.path[1]
                if grid[next[0]][next[1]] > 1:
                    self.movement_path.clear()
                    self.path.clear()


    def move_input(self, dx, dy, grid, enemys):
        tempx = int(self.posX/4)
        tempy = int(self.posY/4)

        map = []

        for i in range(len(grid)):
            map.append([])
            for j in range(len(grid[i])):
                map[i].append(grid[i][j])

        for x in enemys:
            if x == self:
                continue
            elif not x.life:
                continue
            else:
                map[int(x.posX/4)][int(x.posY/4)] = 2

        if self.posX % 4 != 0 and dx == 0:
            if self.posX % 4 == 1:
                self.posX -= 1
            elif self.posX % 4 == 3:
                self.posX += 1
            return
        if self.posY % 4 != 0 and dy == 0:
            if self.posY % 4 == 1:
                self.posY -= 1
            elif self.posY % 4 == 3:
                self.posY += 1
            return

        # right
        if dx == 1:
            if map[tempx+1][tempy] == 0:
                self.posX += 1
        # left
        elif dx == -1:
            tempx = math.ceil(self.posX / 4)
            if map[tempx-1][tempy] == 0:
                self.posX -= 1

        # bottom
        if dy == 1:
            if map[tempx][tempy+1] == 0:
                self.posY += 1
        # top
        elif dy == -1:
            tempy = math.ceil(self.posY / 4)
            if map[tempx][tempy-1] == 0:
                self.posY -= 1
                


    def getActionMove(self, map, bombs, explosions, enemy,x,y):
        bomb = None
        
        with self.lock:
            #print(self.cli.gamestate.players)
            
            if self.id not in self.cli.gamestate.players:
                self.life = False
            #    print('it works maybe? ',self.id,' died')
                return
            
            if self.id in self.cli.gamestate.bombs:
                bomb = self.cli.gamestate.bombs[self.id] 
            
            new_x, new_y = self.cli.gamestate.get_player_positions()[self.id]  
         
        
        dx = None
        dy = None
        nx = new_x*4
        ny = new_y*4
        
        
        if x == nx:
            dx = 0
        
        if y == ny:
            dy = 0
        
        #if  x != nx or  y != ny:
            #print('x',x,nx)
            #print('y',y,ny)
        
        if x + 4 == nx:
            dx = 1
    
        if x - 4 == nx:
            dx = -1
            
        if y + 4 == ny:
            dy = 1
            
        if y - 4 == ny:
            dy = -1
            
        #print(dx,dy)
        
        #self.move_input(dx,dy,map,enemy)
        self.posX = nx
        self.posY = ny
        
        
        if bomb:
            #print(bomb)
            bombs.append(self.plant_bomb(map))
            map[int(self.posX / 4)][int(self.posY / 4)] = 3
            self.cli.gamestate.bombs.pop(self.id)
        


            
    
    def make_move(self, map, bombs, explosions, enemy):
        if not self.life:
            return
        
        if self.algorithm is Algorithm.REMOTE:
            self.getActionMove(map,bombs,explosions,enemy,self.posX,self.posY)
        else:    
            if len(self.movement_path) == 0:
                if self.plant:
                    self.sendAction('bomb',self.posX,self.posY)
                    bombs.append(self.plant_bomb(map))
                    self.plant = False
                    map[int(self.posX / 4)][int(self.posY / 4)] = 3
                if self.algorithm is Algorithm.DFS:
                    self.dfs(self.create_grid(map, bombs, explosions, enemy))
                elif self.algorithm is Algorithm.DIJKSTRA:
                    self.dijkstra(self.create_grid_dijkstra(map, bombs, explosions, enemy))
                  
            else:
                self.direction = self.movement_path[0]
                x = self.posX
                y = self.posY
                self.move(map, bombs, explosions, enemy)
                self.sendAction('move',x,y)

    def plant_bomb(self, map):
        b = Bomb(self.range, round(self.posX / 4), round(self.posY / 4), map, self)
        self.bomb_limit -= 1
        return b

    def check_death(self, exp):
        
        for e in exp:
            for s in e.sectors:
                if int(self.posX / 4) == s[0] and int(self.posY / 4) == s[1]:
                    if e.bomber == self:
                        print(str(self.algorithm.value) + " Self Wrecked")
                    self.life = False
                    return False
        return True
        

    def dfs(self, grid):

        new_path = [[int(self.posX / 4), int(self.posY / 4)]]
        depth = 0
        if self.bomb_limit == 0:
            self.dfs_rec(grid, 0, new_path, depth)
        else:
            self.dfs_rec(grid, 2, new_path, depth)

        self.path = new_path

    def dfs_rec(self, grid, end, path, depth):

        last = path[-1]
        if depth > 200:
            return
        if grid[last[0]][last[1]] == 0 and end == 0:
            return
        elif end == 2:
            if grid[last[0] + 1][last[1]] == end or grid[last[0] - 1][last[1]] == end \
                    or grid[last[0]][last[1] + 1] == end \
                    or grid[last[0]][last[1] - 1] == end:
                if len(path) == 1 and end == 2:
                    self.plant = True
                return

        grid[last[0]][last[1]] = 9

        random.shuffle(self.dire)

        # safe
        if grid[last[0] + self.dire[0][0]][last[1] + self.dire[0][1]] == 0:
            path.append([last[0] + self.dire[0][0], last[1] + self.dire[0][1]])
            self.movement_path.append(self.dire[0][2])
        elif grid[last[0] + self.dire[1][0]][last[1] + self.dire[1][1]] == 0:
            path.append([last[0] + self.dire[1][0], last[1] + self.dire[1][1]])
            self.movement_path.append(self.dire[1][2])
        elif grid[last[0] + self.dire[2][0]][last[1] + self.dire[2][1]] == 0:
            path.append([last[0] + self.dire[2][0], last[1] + self.dire[2][1]])
            self.movement_path.append(self.dire[2][2])
        elif grid[last[0] + self.dire[3][0]][last[1] + self.dire[3][1]] == 0:
            path.append([last[0] + self.dire[3][0], last[1] + self.dire[3][1]])
            self.movement_path.append(self.dire[3][2])

        # unsafe
        elif grid[last[0] + self.dire[0][0]][last[1] + self.dire[0][1]] == 1:
            path.append([last[0] + self.dire[0][0], last[1] + self.dire[0][1]])
            self.movement_path.append(self.dire[0][2])
        elif grid[last[0] + self.dire[1][0]][last[1] + self.dire[1][1]] == 1:
            path.append([last[0] + self.dire[1][0], last[1] + self.dire[1][1]])
            self.movement_path.append(self.dire[1][2])
        elif grid[last[0] + self.dire[2][0]][last[1] + self.dire[2][1]] == 1:
            path.append([last[0] + self.dire[2][0], last[1] + self.dire[2][1]])
            self.movement_path.append(self.dire[2][2])
        elif grid[last[0] + self.dire[3][0]][last[1] + self.dire[3][1]] == 1:
            path.append([last[0] + self.dire[3][0], last[1] + self.dire[3][1]])
            self.movement_path.append(self.dire[3][2])
        else:
            if len(self.movement_path) > 0:
                path.pop(0)
                self.movement_path.pop(0)
        depth += 1
        self.dfs_rec(grid, end, path, depth)

    def dijkstra(self, grid):

        end = 1
        if self.bomb_limit == 0:
            end = 0

        visited = []
        open_list = []
        current = grid[int(self.posX / 4)][int(self.posY / 4)]
        current.weight = current.base_weight
        new_path = []
        while True:
            visited.append(current)
            random.shuffle(self.dire)
            if (current.value == end and end == 0) or\
                    (end == 1 and (grid[current.x+1][current.y].value == 1 or grid[current.x-1][current.y].value == 1 or
                grid[current.x][current.y+1].value == 1 or grid[current.x][current.y-1].value == 1)):
                new_path.append([current.x, current.y])
                while True:
                    if current.parent is None:
                        break
                    current = current.parent
                    new_path.append([current.x, current.y])
                new_path.reverse()
                for xd in range(len(new_path)):
                    if new_path[xd] is not new_path[-1]:
                        if new_path[xd][0] - new_path[xd+1][0] == -1:
                            self.movement_path.append(1)
                        elif new_path[xd][0] - new_path[xd + 1][0] == 1:
                            self.movement_path.append(3)
                        elif new_path[xd][1] - new_path[xd + 1][1] == -1:
                            self.movement_path.append(0)
                        elif new_path[xd][1] - new_path[xd + 1][1] == 1:
                            self.movement_path.append(2)
                if len(new_path) == 1 and end == 1:
                    self.plant = True
                self.path = new_path
                return

            for i in range(len(self.dire)):
                if current.x + self.dire[i][0] < len(grid) and current.y + self.dire[i][1] < len(grid):
                    if grid[current.x + self.dire[i][0]][current.y + self.dire[i][1]].reach \
                            and grid[current.x + self.dire[i][0]][current.y + self.dire[i][1]] not in visited:
                        if grid[current.x + self.dire[i][0]][current.y + self.dire[i][1]] in open_list:
                            if grid[current.x + self.dire[i][0]][current.y + self.dire[i][1]].weight >\
                                    grid[current.x][current.y].weight \
                                    + grid[current.x + self.dire[i][0]][current.y + self.dire[i][1]].base_weight:
                                grid[current.x + self.dire[i][0]][current.y + self.dire[i][1]].parent = current
                                grid[current.x + self.dire[i][0]][current.y + self.dire[i][1]].weight = current.weight + grid[current.x + self.dire[i][0]][current.y + self.dire[i][1]].base_weight
                                grid[current.x + self.dire[i][0]][current.y + self.dire[i][1]].direction = self.dire[i][2]

                        else:
                            grid[current.x + self.dire[i][0]][current.y + self.dire[i][1]].parent = current
                            grid[current.x + self.dire[i][0]][current.y + self.dire[i][1]].weight =\
                                current.weight + grid[current.x + self.dire[i][0]][current.y + self.dire[i][1]].base_weight
                            grid[current.x + self.dire[i][0]][current.y + self.dire[i][1]].direction = self.dire[i][2]
                            open_list.append(grid[current.x + self.dire[i][0]][current.y + self.dire[i][1]])

            if len(open_list) == 0:
                self.path = [[int(self.posX / 4), int(self.posY / 4)]]
                return

            next_node = open_list[0]
            for n in open_list:
                if n.weight < next_node.weight:
                    next_node = n
            open_list.remove(next_node)
            current = next_node


    def create_grid(self, map, bombs, explosions, enemys):
        grid = [[0] * len(map) for r in range(len(map))]

        # 0 - safe
        # 1 - unsafe
        # 2 - destryable
        # 3 - unreachable

        for b in bombs:
            b.get_range(map)
            for x in b.sectors:
                grid[x[0]][x[1]] = 1
            grid[b.posX][b.posY] = 3

        for e in explosions:
            for s in e.sectors:
                grid[s[0]][s[1]] = 3

        for i in range(len(map)):
            for j in range(len(map[i])):
                if map[i][j] == 1:
                    grid[i][j] = 3
                elif map[i][j] == 2:
                    grid[i][j] = 2

        for x in enemys:
            if x == self:
                continue
            elif not x.life:
                continue
            else:
                grid[int(x.posX / 4)][int(x.posY / 4)] = 2

        return grid

    def create_grid_dijkstra(self, map, bombs, explosions, enemys):
        grid = [[None] * len(map) for r in range(len(map))]

        # 0 - safe
        # 1 - destroyable
        # 2 - unreachable
        # 3 - unsafe
        for i in range(len(map)):
            for j in range(len(map)):
                if map[i][j] == 0:
                    grid[i][j] = Node(i, j, True, 1, 0)
                elif map[i][j] == 2:
                    grid[i][j] = Node(i, j, False, 999, 1)
                elif map[i][j] == 1:
                    grid[i][j] = Node(i, j, False, 999, 2)
                elif map[i][j] == 3:
                    grid[i][j] = Node(i, j, False, 999, 2)

        for b in bombs:
            b.get_range(map)
            for x in b.sectors:
                grid[x[0]][x[1]].weight = 5
                grid[x[0]][x[1]].value = 3
            grid[b.posX][b.posY].reach = False

        for e in explosions:
            for s in e.sectors:
                grid[s[0]][s[1]].reach = False

        for x in enemys:
            if x == self:
                continue
            elif not x.life:
                continue
            else:
                grid[int(x.posX / 4)][int(x.posY / 4)].reach = False
                grid[int(x.posX / 4)][int(x.posY / 4)].value = 1
        return grid

    def load_animations(self, en, scale):
        front = []
        back = []
        left = []
        right = []
        resize_width = scale
        resize_height = scale

        image_path = 'images/enemy/e'
        if en == '':
            image_path = 'images/hero/p'

        f1 = pygame.image.load(image_path + en + 'f0.png')
        f2 = pygame.image.load(image_path + en + 'f1.png')
        f3 = pygame.image.load(image_path + en + 'f2.png')

        f1 = pygame.transform.scale(f1, (resize_width, resize_height))
        f2 = pygame.transform.scale(f2, (resize_width, resize_height))
        f3 = pygame.transform.scale(f3, (resize_width, resize_height))

        front.append(f1)
        front.append(f2)
        front.append(f3)

        r1 = pygame.image.load(image_path + en + 'r0.png')
        r2 = pygame.image.load(image_path + en + 'r1.png')
        r3 = pygame.image.load(image_path + en + 'r2.png')

        r1 = pygame.transform.scale(r1, (resize_width, resize_height))
        r2 = pygame.transform.scale(r2, (resize_width, resize_height))
        r3 = pygame.transform.scale(r3, (resize_width, resize_height))

        right.append(r1)
        right.append(r2)
        right.append(r3)

        b1 = pygame.image.load(image_path + en + 'b0.png')
        b2 = pygame.image.load(image_path + en + 'b1.png')
        b3 = pygame.image.load(image_path + en + 'b2.png')

        b1 = pygame.transform.scale(b1, (resize_width, resize_height))
        b2 = pygame.transform.scale(b2, (resize_width, resize_height))
        b3 = pygame.transform.scale(b3, (resize_width, resize_height))

        back.append(b1)
        back.append(b2)
        back.append(b3)

        l1 = pygame.image.load(image_path + en + 'l0.png')
        l2 = pygame.image.load(image_path + en + 'l1.png')
        l3 = pygame.image.load(image_path + en + 'l2.png')

        l1 = pygame.transform.scale(l1, (resize_width, resize_height))
        l2 = pygame.transform.scale(l2, (resize_width, resize_height))
        l3 = pygame.transform.scale(l3, (resize_width, resize_height))

        left.append(l1)
        left.append(l2)
        left.append(l3)

        self.animation.append(front)
        self.animation.append(right)
        self.animation.append(back)
        self.animation.append(left)

