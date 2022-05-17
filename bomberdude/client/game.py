from numpy import tile
import pygame
import sys
import random
import time
from common.state import state
from .player import Player
from .explosion import Explosion
from .enemy import Enemy
from .algorithm import Algorithm
from common.payload import ACTIONS, KALIVE, REJOIN, STATE, Payload, ACCEPT, LEAVE, JOIN, REDIRECT, REJECT
from common.state import Change
from threading import Thread

TILE_WIDTH = 40
TILE_HEIGHT = 40

WINDOW_WIDTH = 13 * TILE_WIDTH
WINDOW_HEIGHT = 13 * TILE_HEIGHT

BACKGROUND = (107, 142, 35)


s = None
show_path = True

clock = None

player = None
enemy_list = []
ene_blocks = []
bombs = []
explosions = []

#grid = state

grid = [[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
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
       

grass_img = None
block_img = None
box_img = None
bomb1_img = None
bomb2_img = None
bomb3_img = None
explosion1_img = None
explosion2_img = None
explosion3_img = None


terrain_images = []
bomb_images = []
explosion_images = []

pygame.font.init()
font = pygame.font.SysFont('Bebas', 30)
TEXT_LOSE = font.render('GAME OVER', False, (0, 0, 0))
TEXT_WIN = font.render('WIN', False, (0, 0, 0))

def game_init(path, player_alg, en1_alg, en2_alg, en3_alg, scale,cli,args):
    
    Thread(target=start_server,args=(cli,args)).start()
    
    cli.gamestate.reset()
    while not cli.player_id:
            print("waiting for players")
    #        print(f'player_id: {cli.player_id}')
            time.sleep(1)
            
    global TILE_WIDTH
    global TILE_HEIGHT
    TILE_WIDTH = scale
    TILE_HEIGHT = scale

    global font
    font = pygame.font.SysFont('Bebas', scale)

    global show_path
    show_path = path

    global s
    s = pygame.display.set_mode((13 * TILE_WIDTH, 13 * TILE_HEIGHT))
    pygame.display.set_caption('Bomberdude')

    global clock
    clock = pygame.time.Clock()

    global enemy_list
    global ene_blocks
    global boxes
    global player

    enemy_list = []
    ene_blocks = []
    boxes = {}
    global explosions
    global bombs
    bombs.clear()
    explosions.clear()
        
    '''
    if en1_alg is not Algorithm.NONE:
        en1 = Enemy(11, 1, Algorithm.DFS,cli,2)
        en1.load_animations('1', scale)
        enemy_list.append(en1)
        ene_blocks.append(en1)

    if en2_alg is not Algorithm.NONE:
        en2 = Enemy(1, 11, Algorithm.DFS,cli,3)
        en2.load_animations('2', scale)
        enemy_list.append(en2)
        ene_blocks.append(en2)

    if en3_alg is not Algorithm.NONE:
        en3 = Enemy(11, 11, Algorithm.DFS,cli,4)
        en3.load_animations('3', scale)
        enemy_list.append(en3)
        ene_blocks.append(en3)
    '''
    global en0

    player_alg = Algorithm.DFS
    
    if cli.player_id == 1:
        player = Player(1,1)
        if player_alg is Algorithm.PLAYER:
            player.load_animations('', scale)
            ene_blocks.append(player)
            
            
        elif player_alg is not Algorithm.NONE:
            en0 = Enemy(1, 1, player_alg,cli,1)
            en0.load_animations('', scale)
            enemy_list.append(en0)
            ene_blocks.append(en0)
            player.life = False
        else:
            player.life = False
            
        en1 = Enemy(11, 1, Algorithm.REMOTE,cli,2)
        en1.load_animations('2', scale)
        enemy_list.append(en1)
        ene_blocks.append(en1)

        en2 = Enemy(1, 11, Algorithm.REMOTE,cli,3)
        en2.load_animations('1', scale)
        enemy_list.append(en2)
        ene_blocks.append(en2)

        en3 = Enemy(11, 11, Algorithm.REMOTE,cli,4)
        en3.load_animations('3', scale)
        enemy_list.append(en3)
        ene_blocks.append(en3)
            
    elif cli.player_id == 2:
        player = Player(11,1)
        if player_alg is Algorithm.PLAYER:
            player.load_animations('2', scale)
            ene_blocks.append(player)
            
        elif player_alg is not Algorithm.NONE:
            en0 = Enemy(11, 1, player_alg,cli,2)
            en0.load_animations('2', scale)
            enemy_list.append(en0)
            ene_blocks.append(en0)
            player.life = False
        else:
            player.life = False
            
        en1 = Enemy(1, 1, Algorithm.REMOTE,cli,1)
        en1.load_animations('', scale)
        enemy_list.append(en1)
        ene_blocks.append(en1)

        en2 = Enemy(1, 11, Algorithm.REMOTE,cli,3)
        en2.load_animations('1', scale)
        enemy_list.append(en2)
        ene_blocks.append(en2)

        en3 = Enemy(11, 11, Algorithm.REMOTE,cli,4)
        en3.load_animations('3', scale)
        enemy_list.append(en3)
        ene_blocks.append(en3)

    elif cli.player_id == 3:
        player = Player(1,11)
        if player_alg is Algorithm.PLAYER:
            player.load_animations('1', scale)
            ene_blocks.append(player)
            
        elif player_alg is not Algorithm.NONE:
            en0 = Enemy(1, 11, player_alg,cli,3)
            en0.load_animations('1', scale)
            enemy_list.append(en0)
            ene_blocks.append(en0)
            player.life = False
        else:
            player.life = False
            
        en1 = Enemy(11, 1, Algorithm.REMOTE,cli,2)
        en1.load_animations('2', scale)
        enemy_list.append(en1)
        ene_blocks.append(en1)

        en2 = Enemy(1, 1, Algorithm.REMOTE,cli,1)
        en2.load_animations('', scale)
        enemy_list.append(en2)
        ene_blocks.append(en2)

        en3 = Enemy(11, 11, Algorithm.REMOTE,cli,4)
        en3.load_animations('3', scale)
        enemy_list.append(en3)
        ene_blocks.append(en3)

    elif cli.player_id == 4:
        player = Player(11,11)
        if player_alg is Algorithm.PLAYER:
            player.load_animations('3', scale)
            ene_blocks.append(player)
            
        elif player_alg is not Algorithm.NONE:
            en0 = Enemy(11, 11, player_alg,cli,4)
            en0.load_animations('3', scale)
            enemy_list.append(en0)
            ene_blocks.append(en0)
            player.life = False
        else:
            player.life = False
            
        en1 = Enemy(11, 1, Algorithm.REMOTE,cli,2)
        en1.load_animations('2', scale)
        enemy_list.append(en1)
        ene_blocks.append(en1)

        en2 = Enemy(1, 11, Algorithm.REMOTE,cli,3)
        en2.load_animations('1', scale)
        enemy_list.append(en2)
        ene_blocks.append(en2)

        en3 = Enemy(1, 1, Algorithm.REMOTE,cli,1)
        en3.load_animations('', scale)
        enemy_list.append(en3)
        ene_blocks.append(en3)
    '''
    player_alg = Algorithm.DFS
    player = Player(1,1)
    if player_alg is Algorithm.PLAYER:
        player.load_animations(scale)
        ene_blocks.append(player)
    elif player_alg is not Algorithm.NONE:
        en0 = Enemy(1, 1, player_alg,cli,1)
        en0.load_animations('', scale)
        player.load_animations(scale)
        enemy_list.append(en0)
        ene_blocks.append(en0)
        player.life = False
    else:
        player.life = False
    '''

    global grass_img
    grass_img = pygame.image.load('images/terrain/grass.png')
    grass_img = pygame.transform.scale(grass_img, (TILE_WIDTH, TILE_HEIGHT))
    global block_img
    block_img = pygame.image.load('images/terrain/block.png')
    block_img = pygame.transform.scale(block_img, (TILE_WIDTH, TILE_HEIGHT))
    global box_img
    box_img = pygame.image.load('images/terrain/box.png')
    box_img = pygame.transform.scale(box_img, (TILE_WIDTH, TILE_HEIGHT))
    global bomb1_img
    bomb1_img = pygame.image.load('images/bomb/1.png')
    bomb1_img = pygame.transform.scale(bomb1_img, (TILE_WIDTH, TILE_HEIGHT))
    global bomb2_img
    bomb2_img = pygame.image.load('images/bomb/2.png')
    bomb2_img = pygame.transform.scale(bomb2_img, (TILE_WIDTH, TILE_HEIGHT))
    global bomb3_img
    bomb3_img = pygame.image.load('images/bomb/3.png')
    bomb3_img = pygame.transform.scale(bomb3_img, (TILE_WIDTH, TILE_HEIGHT))
    global explosion1_img
    explosion1_img = pygame.image.load('images/explosion/1.png')
    explosion1_img = pygame.transform.scale(explosion1_img, (TILE_WIDTH, TILE_HEIGHT))
    global explosion2_img
    explosion2_img = pygame.image.load('images/explosion/2.png')
    explosion2_img = pygame.transform.scale(explosion2_img, (TILE_WIDTH, TILE_HEIGHT))
    global explosion3_img
    explosion3_img = pygame.image.load('images/explosion/3.png')
    explosion3_img = pygame.transform.scale(explosion3_img, (TILE_WIDTH, TILE_HEIGHT))
    global terrain_images
    terrain_images = [grass_img, block_img, box_img, grass_img]
    global bomb_images
    bomb_images = [bomb1_img, bomb2_img, bomb3_img]
    global explosion_images
    explosion_images = [explosion1_img, explosion2_img, explosion3_img]

    main(cli)


def draw():
    s.fill(BACKGROUND)
    for i in range(len(grid)):
        for j in range(len(grid[i])):
            s.blit(terrain_images[grid[i][j]], (i * TILE_WIDTH, j * TILE_HEIGHT, TILE_HEIGHT, TILE_WIDTH))

    for x in bombs:
        s.blit(bomb_images[x.frame], (x.posX * TILE_WIDTH, x.posY * TILE_HEIGHT, TILE_HEIGHT, TILE_WIDTH))

    for y in explosions:
        for x in y.sectors:
            s.blit(explosion_images[y.frame], (x[0] * TILE_WIDTH, x[1] * TILE_HEIGHT, TILE_HEIGHT, TILE_WIDTH))
    if player.life:
        s.blit(player.animation[player.direction][player.frame],
               (player.posX * (TILE_WIDTH / 4), player.posY * (TILE_HEIGHT / 4), TILE_WIDTH, TILE_HEIGHT))
    for en in enemy_list:
        if en.life:
            s.blit(en.animation[en.direction][en.frame],
                   (en.posX * (TILE_WIDTH / 4), en.posY * (TILE_HEIGHT / 4), TILE_WIDTH, TILE_HEIGHT))
    pygame.display.update()


def generate_map(cli):
    if not cli.gamestate.boxes:
        time.sleep(0.1)
    
    boxes.update(cli.gamestate.boxes)
    
    
    for box in cli.gamestate.boxes.items():
        grid[box[1][0]][box[1][1]] = 2
    return

def sendAction(cli,action,x,y):
    if action == '':
        return
    
    move_x,move_y = player.position()
    
    tile_id = None      
    match action:
        case 'move' : tile_id = cli.player_id + 9
        case 'bomb': tile_id = 2 
        case 'death': tile_id = cli.player_id + 109
        case _: return
    
    data = Change((int(x/4),int(y/4),cli.player_id+9),(int(move_x/4),int(move_y/4),tile_id))
    print('sent action',data)
    cli.seq_num += 1
    payload = Payload(ACTIONS, data.to_bytes(), cli.lobby_uuid,
                    cli.player_uuid, cli.seq_num)
    
    cli.unicast(payload.to_bytes())
    

def main(cli):
    generate_map(cli)
    while player.life:
        dt = clock.tick(15)
        for en in enemy_list:
            en.make_move(grid, bombs, explosions, ene_blocks)
        keys = pygame.key.get_pressed()
        temp = player.direction
        movement = False
        if keys[pygame.K_DOWN]:
            x,y = player.position()
            temp = 0
            player.move(0, 1, grid, ene_blocks)
            sendAction(cli,'move',x,y)
            movement = True
        elif keys[pygame.K_RIGHT]:
            x,y = player.position()
            temp = 1
            player.move(1, 0, grid, ene_blocks)
            sendAction(cli,'move',x,y)
            movement = True
        elif keys[pygame.K_UP]:
            x,y = player.position()
            temp = 2
            player.move(0, -1, grid, ene_blocks)
            sendAction(cli,'move',x,y)
            movement = True
        elif keys[pygame.K_LEFT]:
            x,y = player.position()
            temp = 3
            player.move(-1, 0, grid, ene_blocks)
            sendAction(cli,'move',x,y)
            movement = True
            
        if temp != player.direction:
            player.frame = 0
            player.direction = temp
        if movement:
            if player.frame == 2:
                player.frame = 0
            else:
                player.frame += 1

        draw()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                sys.exit(0)
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    if player.bomb_limit == 0:
                        continue
                    x,y = player.position()
                    sendAction(cli,'bomb',x,y)
                    temp_bomb = player.plant_bomb(grid)
                    bombs.append(temp_bomb)
                    grid[temp_bomb.posX][temp_bomb.posY] = 3
                    player.bomb_limit -= 1
                    

        update_bombs(cli,dt)
    game_over(cli)

def sync_boxes(cli):
    state_boxes = cli.gamestate.boxes.keys()
    client_boxes = boxes.keys()
    
    diff = client_boxes - state_boxes
    
    for i in diff:
        x,y = boxes[i]
        boxes.pop(i)
        grid[x][y] = 0
    

def update_bombs(cli,dt):
    for b in bombs:
        b.update(dt)
        if b.time < 1:
            b.bomber.bomb_limit += 1
            grid[b.posX][b.posY] = 0
            exp_temp = Explosion(b.posX, b.posY, b.range,cli)
            exp_temp.explode(grid, bombs, b)
            exp_temp.clear_sectors(grid,boxes)
            sync_boxes(cli)
            explosions.append(exp_temp)
            
    if en0 not in enemy_list:
        if player.life:
            check = player.check_death(explosions)
            if check == False:
                print('player: ',cli.player_id)
                x,y = player.position()
                sendAction(cli,'death',x,y)
            
    for en in enemy_list:
        if en.algorithm != Algorithm.REMOTE:
            if en.life:
                check = en.check_death(explosions)
                if check == False:
                    #cli.gamestate.players.pop(en.id)
                    #print('enemy ',en.id)
                    x,y = player.position()
                    sendAction(cli,'death',x,y)
    for e in explosions:
        e.update(dt)
        if e.time < 1:
            explosions.remove(e)


def start_server(cli,args):
    cli.join_server(args.id)
    cli.start()

def game_over(cli):
    while True:
        dt = clock.tick(15)
        update_bombs(cli,dt)
        count = 0
        winner = ""
        for en in enemy_list:
            en.make_move(grid, bombs, explosions, ene_blocks)
            if en.life:
                count += 1
                winner = en.algorithm.name
        if count == 1:
            draw()
            textsurface = font.render(winner + " wins", False, (0, 0, 0))
            font_w = textsurface.get_width()
            font_h = textsurface.get_height()
            s.blit(textsurface, (s.get_width() // 2 - font_w//2,  s.get_height() // 2 - font_h//2))
            pygame.display.update()
            time.sleep(2)
            break
        if count == 0:
            draw()
            textsurface = font.render("Draw", False, (0, 0, 0))
            font_w = textsurface.get_width()
            font_h = textsurface.get_height()
            s.blit(textsurface, (s.get_width() // 2 - font_w//2, s.get_height() // 2 - font_h//2))
            pygame.display.update()
            time.sleep(2)
            break
        draw()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                sys.exit(0)
    explosions.clear()
    enemy_list.clear()
    ene_blocks.clear()
