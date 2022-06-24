from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import time, threading, socket
from random import randint
from tcp_by_size import send_with_size, recv_by_size
# encryption imports:
import json
from base64 import b64encode, b64decode
from Crypto.Cipher import ChaCha20

# Global variables used for setting up connection
tcp_sock = socket.socket()

#TODO: change it back to input
IP = "192.168.1.245"
PORT = 9320
key = 0
nickname = ""
lobby = ""
password = ""
hp = 100
threads = {}
alive = True
last_loc_send = time.perf_counter()
my_player = None # this client's player
shooting = False # my player's shooting status

def recv():
    global tcp_sock

    byte_data = recv_by_size(tcp_sock)
    print(byte_data)
    if byte_data == b'':
        return ""
    else:
        return decrypt(byte_data)

def encrypt_send(sock, text):
    global key

    #encrypt
    cipher = ChaCha20.new(key=key)
    ciphertext = cipher.encrypt(text.encode("utf-8"))
    # get the nonce and text and build message
    nonce = b64encode(cipher.nonce).decode("utf-8")
    ct = b64encode(ciphertext).decode("utf-8")
    result = json.dumps({'nonce':nonce, 'ciphertext':ct})
    # send the result to the server
    send_with_size(sock, result)

def decrypt(data):
    try:
        # split dictionary to ciphertext and nonce
        b64 = json.loads(data)
        nonce = b64decode(b64['nonce'])
        ciphertext = b64decode(b64['ciphertext'])
        # decrypt
        cipher = ChaCha20.new(key=key, nonce=nonce)
        text = cipher.decrypt(ciphertext).decode("utf-8")

        #TODO: remove print
        print(f"RECEIVED - {text}")

        return text

    except (ValueError, KeyError):
        print("Incorrect decryption")

def diffie_hellman(sock):
    global key, tcp_sock

    n = 1008001 # relatively large prime number
    g = 151 # small prime number
    a = random.randint(0, n)

    bg = int(recv_by_size(tcp_sock).decode("utf-8"))
    ag = (g**a) % n
    send_with_size(sock, str(ag))

    key = (bg**a) % n
    key = key.to_bytes(32, "little")

def handle_response(sock, data):
    global lobby, password, hp, alive, walking_speed, my_player, alive
    if data == "CREATED":
        return "CREATED"
    elif data == "JOINED":
        return "JOINED"
    elif data == "GAMEON":
        return "GAMEON"
    elif data.startswith("HIT"):
        splits = data.split("~")
        # split 0 - command, 1 - lobby, 2 - player who was hit, 3 - player who shot him
        if splits[2] == nickname:
            if hp <= 20:
                encrypt_send(tcp_sock, f"DEAD~{lobby}~{nickname}~{splits[3]}")
                alive = False
            else:
                hp -= 20
                hp_text.text = f"hp: {hp}"
    elif data.startswith("DEAD"):
        splits = data.split("~")
        # split 0 - command, 1 - lobby, 2 - player who was killed, 3 - player who killed him
        if splits[2] != nickname:
            enemies[splits[2]].update_death(True)
            #TODO: add point to killer
    elif data.startswith("LOC"):
        splits = data.split("~")
        #split 0 - command, 1 - player, 2 - x, 3 - y, 4 - z, 5 - shooting (T or F), TODO: add rotation
        #check if the message is for/from you
        if splits[1] == nickname:
            if not alive:
                my_player = FirstPersonController(position = (float(splits[2]), float(splits[3]) + 2, float(splits[4])))
                my_player.cursor.color = color.white
                walking_speed = my_player.speed
                alive = True
                hp = 100
                hp_text.text = f"hp: {hp}"
        else:
            #check if the enemy was already created
            if splits[1] in enemies:
                enemies[splits[1]].update_death(False)
                #TODO: add rotation support
                x, y, z = enemies[splits[1]].get_loc()
                if x != splits[2] and y != splits[3] and z != splits[4]:
                    enemies[splits[1]].update_walk(True)
                    if splits[5] == "T":
                        enemies[splits[1]].update_loc(float(splits[2]), float(splits[3]), float(splits[4]))
                        enemies[splits[1]].update_shooting(True)
                    else:
                        enemies[splits[1]].update_loc(float(splits[2]), float(splits[3]), float(splits[4]))
                        enemies[splits[1]].update_shooting(False)
                else:
                    enemies[splits[1]].update_walk(False)
                    if splits[5] == "T":
                        enemies[splits[1]].update_shooting(True)
                    else:
                        enemies[splits[1]].update_shooting(False)
            else:
                enemies[splits[1]] = Enemy(splits[1], float(splits[2]), float(splits[3]), float(splits[4]), False, False)
    elif data.startswith("ERROR"):
        if data == "ERROR~TAKEN":
            lobby = input("Name is taken, please enter a different name: ")
            while True:
                message = f"NEW~{nickname}~{lobby}~{password}"
                encrypt_send(sock, message)
                if recv() == "CREATED":
                    return "CREATED"
        # check wrong password
        elif data[6:] == "password":
            while True:
                password = input("Wrong password, please try again: ")
                message = f"JOIN~{nickname}~{lobby}~{password}"
                encrypt_send(sock, message)
                if recv() == "JOINED":
                    return "JOINED"
        # check invalid name
        elif data[6:] == "name":
            while True:
                password = input("Invalid name, please try again: ")
                message = f"JOIN~{nickname}~{lobby}~{password}"
                encrypt_send(sock, message)
                if recv() == "JOINED":
                    return "JOINED"
        elif data[6:] == "not_host":
            return "not_host"

def menu():
    """
    Takes care of start menu before the game begins
    """
    global nickname, tcp_sock, lobby, password

    connected = False
    try:
        tcp_sock.connect((IP, PORT))
        print(f'Connect succeeded {IP}:{PORT}')
        connected = True
    except:
        print(f'Error while trying to connect.  Check ip or port -- {IP}:{PORT}')
        return False
    
    if connected:
        diffie_hellman(tcp_sock)

        nickname = input("Please enter your nickname: ")
        inp = input("Enter T to create a new lobby\nor enter F to join a lobby: ").upper()
        if inp == "T":
            lobby = input("Please enter the lobby's name: ")
            password = input("Please enter the lobby's password: ")
            message = f"NEW~{nickname}~{lobby}~{password}"
            encrypt_send(tcp_sock, message)
            # try again until the name is good
            created = False
            received = recv()
            # lobby was created
            if handle_response(tcp_sock, received) == "CREATED":
                input("Press ENTER when everyone's ready to start the game")
                message = f"READY~{nickname}~{lobby}~{password}"
                encrypt_send(tcp_sock, message)
                received = recv()
                # if game is ready
                if received == "GAMEON":
                    return True
                else:
                    print("Error when attempting to start game")
                    sys.exit()
            else:
                print("Unable to create lobby")
                sys.exit()

        elif inp == "F":
            lobby = input("Please enter the lobby's name: ")
            password = input("Please enter the lobby's password: ")
            message = f"JOIN~{nickname}~{lobby}~{password}"
            encrypt_send(tcp_sock, message)
            joined = False
            # check if there were any errors
            received = recv()
            if handle_response(tcp_sock, received) == "JOINED":
                print("Joined successfully, waiting for host to start the game...")
                received = recv()
                # if game is ready
                if handle_response(tcp_sock, received) == "GAMEON":
                    return True
                else:
                    print("Error when attempting to start game")
                    sys.exit()
            else:
                print("Unable to join lobby")
                sys.exit()
        
        else:
            print("Invalid answer, please rerun and try again")
            sys.exit()


start = menu()
if not start:
    sys.exit()
application.development_mode = False
app = Ursina() # creating a window

class Bullet(Entity):
    def __init__(self, speed=20, lifetime=1, **kwargs):
        super().__init__(**kwargs)
        self.speed = speed
        self.lifetime = lifetime
        self.start = time.time()

    def update(self):
        ray = raycast(self.world_position, self.forward, distance=self.speed*time.dt)
        if not ray.hit and time.time() - self.start < self.lifetime:
            self.world_position += self.forward * self.speed * time.daylight
        else:
            destroy(self)

class Enemy():
    def __init__(self, name, x, y, z, dead, shooting) -> None:
        if shooting:
            self.animation = FrameAnimation3d("shooting_walking/shooting", scale=0.073, position=(x, y, z), autoplay=False)
            self.obj = Entity(model="shooting_walking/shooting1.obj", parent=self.animation, collider="mesh", visible=False)
            self.muzzle_animation = Animation("objs/muzzle_flash.gif", parent=self.animation, y=24, z=24, scale=22, billboard=True)
        else:
            self.animation = FrameAnimation3d("soldier_walking/soldier", scale=0.073, position=(x, y, z), autoplay=False)
            self.obj = Entity(model="soldier_walking/soldier1.obj", parent=self.animation, collider="mesh", visible=False)
            self.muzzle_animation = False
        self.name = name
        self.x = x
        self.y = y
        self.z = z
        self.speed = 0.3
        self.shooting = shooting
        self.dead = dead
        self.walking = False

    def update(self):
        pass
    
    def get_loc(self):
        return self.x, self.y, self.z

    def update_loc(self, x, y, z) -> None:
        self.animation.position = (x, y, z)
        self.x = x
        self.y = y
        self.z = z
    
    def update_rotation(self, rotation) -> None:
        self.animation.rotation = rotation
    
    def update_walk(self, to_walk) -> None:
        if to_walk and not self.walking:
            self.animation.start()
        elif not to_walk and self.walking:
            self.animation.pause()

    def update_death(self, dead):
        # check death
        if not self.dead and dead:
            self.dead = True
            self.animation.visible = False
            self.obj.collider = None

        elif self.dead and not dead:
            self.dead = False
            self.animation.visible = True
            self.obj.collider = "mesh"

    def update_shooting(self, shoot):
        if shoot and not self.shooting:
            self.shooting = True
            pos = self.animation.position
            destroy(self.animation)
            destroy(self.obj)
            destroy(self.muzzle_animation)
            self.animation = FrameAnimation3d("shooting_walking/shooting", scale=0.073, position=pos, autoplay=False)
            self.obj = Entity(model="shooting_walking/shooting1.obj", parent=self.animation, collider="mesh", visible=False)
            self.muzzle_animation = Animation("objs/muzzle_flash.gif", parent=self.animation, y=24, z=24, scale=22, billboard=True)
        elif not shoot and self.shooting:
            self.shooting = False
            pos = self.animation.position
            destroy(self.animation)
            destroy(self.obj)
            destroy(self.muzzle_animation)
            self.animation = FrameAnimation3d("soldier_walking/soldier", scale=0.073, position=pos, autoplay=False)
            self.obj = Entity(model="soldier_walking/soldier1.obj", parent=self.animation, collider="mesh", visible=False)
            self.muzzle_animation = False


# Global variables used for the game
enemies = {} # a dictionary of the other players
walls = []

background_sounds = {
    "birds_singing": Audio("sounds/birds.mp3", autoplay=False, loop=True, volume=.3)
}

ground = Entity(model = "plane", scale = (100, 1, 100), color = color.rgb(0, 255, 25), 
                texture = "grass", texture_scale = (100, 100), collider = "box") # the ground
walking_speed = None

gun = Entity(model="objs/m4", texture = "objs/DiffuseTexture", parent=camera.ui, scale=.13, position = (.42, -.40, -.15),
            rotation=(0, 75, 8))
gun_up = False
moving = False
running = False
m4_sounds = {
    "M4_burst": Audio("sounds/m4_shots/m4_burst.mp3", autoplay=False, volume=2),
    "M4_ending": Audio("sounds/m4_shots/m4_ending2.mp3", autoplay=False, volume=2),
    "last8": Audio("sounds/m4_shots/m4_last8.mp3", autoplay=False, volume=2),
    "last7": Audio("sounds/m4_shots/m4_last7.mp3", autoplay=False, volume=2),
    "last6": Audio("sounds/m4_shots/m4_last6.mp3", autoplay=False, volume=2),
    "last5": Audio("sounds/m4_shots/m4_last5.mp3", autoplay=False, volume=2),
    "last4": Audio("sounds/m4_shots/m4_last4.mp3", autoplay=False, volume=2),
    "last3": Audio("sounds/m4_shots/m4_last3.mp3", autoplay=False, volume=2),
    "last2": Audio("sounds/m4_shots/m4_last2.mp3", autoplay=False, volume=2),
    "last1": Audio("sounds/m4_shots/m4_last1.mp3", autoplay=False, volume=2),
    }
mag = 30
mag_size = Text(f"mag: {mag}", origin=(7, 10))
hp_text = Text(f"hp: {hp}", origin=(7, 4))
last_shot = time.perf_counter()
curr_time = time.perf_counter()


def input(key):
    global mag, mag_size
    if key == 'r' and alive:
        mag = 30
        mag_size.text = f"mag: {mag}"

def m4_sound():
    global shooting, mag
    if mag > 8:
        m4_sounds["M4_burst"].play()
    elif mag == 8:
        m4_sounds["last8"].play()
    elif mag == 7:
        m4_sounds["last7"].play()
    elif mag == 6:
        m4_sounds["last6"].play()
    elif mag == 5:
        m4_sounds["last5"].play()
    elif mag == 4:
        m4_sounds["last4"].play()
    elif mag == 3:
        m4_sounds["last3"].play()
    elif mag == 2:
        m4_sounds["last2"].play()
    elif mag == 1:
        m4_sounds["last1"].play()
        shooting = False


def stop_shooting():
    global mag, shooting
    time.sleep(.05)
    for i in m4_sounds:
        m4_sounds[i].stop()
    m4_sounds["M4_ending"].play()
    

def shoot_check_hit():
    global enemies, tcp_sock, lobby, shooting, my_player

    Bullet(model="sphere", color=color.gold, scale=1, position=my_player.camera_pivot.world_position,
            rotation=my_player.camera_pivot.world_rotation)
    if len(enemies) > 0:
        for enemy in enemies:
            if enemies[enemy].obj.hovered:
                encrypt_send(tcp_sock, f"HIT~{lobby}~{enemy}~{nickname}")
                break


def shooting_sounds():
    global mag, shooting, last_shot, curr_time, mag_size, m4_sounds, lobby, nickname
    #shooting sounds
    if held_keys["left mouse"] and mag > 0:
        if not shooting:
            shooting = True
            last_shot = time.perf_counter()
            mag -= 1
            shoot_check_hit()
            mouse.position = (mouse.x, mouse.y + .04)
            m4_sound()
            mag_size.text = f"mag: {mag}"
        else:
            curr_time = time.perf_counter()
            if curr_time - last_shot >= .085:
                mag -= 1
                shoot_check_hit()
                mouse.position = (mouse.x, mouse.y + .04)
                if mag == 8:
                    m4_sounds["M4_burst"].stop()
                    m4_sounds["last8"].play()
                last_shot = curr_time
                mag_size.text = f"mag: {mag}"
    elif shooting is True:
        if mag > 0:
            x = threading.Thread(target=stop_shooting)
            x.start()
        shooting = False        

def tcp_recv_update():
    global tcp_sock
    #runs in background and deals with incoming messages
    while True:
        received = recv()
        handle_response(tcp_sock, received)

def send_my_location():
    global tcp_sock, nickname, lobby, shooting, my_player

    #TODO:  and add rotation
    if shooting:
        encrypt_send(tcp_sock,f"LOC~{lobby}~{nickname}~{my_player.x}~{my_player.y}~{my_player.z}~T")
    else:
        encrypt_send(tcp_sock,f"LOC~{lobby}~{nickname}~{my_player.x}~{my_player.y}~{my_player.z}~F")

def update():
    """
    Updates values and then renders to screen
    """
    global gun_up, running, moving, enemies, last_loc_send, my_player, alive

    shooting_sounds()
    if alive:
        # check if enough time had passed to send current location
        curr = time.perf_counter()
        if curr - last_loc_send >= 0.15 and alive:
            last_loc_send = curr
            send_my_location()
        if my_player.y <= -5 and alive:
            # make player die
            alive = False
            encrypt_send(tcp_sock, f"DEAD~{lobby}~{nickname}~NO-ONE")
        # moving the gun while walking
        if not shooting:
            if held_keys["shift"]:
                running = True
                my_player.speed = 2 * walking_speed
            elif running == True and not held_keys["shift"]:
                my_player.speed = walking_speed
            if held_keys['w'] or held_keys['s'] or held_keys['d'] or held_keys['a']:
                if not moving:
                    moving = True

                if gun.y > -.6 and not gun_up:
                    gun.y -= .01
                    gun.x -= .008
                    gun.rotation = (gun.x - .4, 75 + gun.y * 20, 8)

                elif gun.y < -.35:
                    gun_up = True
                    gun.y += .008
                    gun.x += .006
                    gun.rotation = (.4 - gun.x, 75 + gun.y * 20, 8)
                else:
                    gun_up = False
                    gun.x = .439
            else:
                gun.position = (.4, -.40, -.1)
                gun.rotation = (0, 75, 8)
        elif moving:
            gun.position = (.4, -.40, -.1)
            gun.rotation = (0, 75, 8)
            moving = False
            running = False
            my_player.speed = walking_speed
        
        for enemy in enemies:
            enemies[enemy].update()

def get_locations():
    global tcp_sock, walls, my_player, walking_speed

    received = None
    while received != "START":
        received = recv()
        if received.startswith("WALL"):
            splits = received.split("~")
            #split 0 - command, 1 - x, 2 - y, 3 - z, 4 - scale_x, 5 - scale_y, 6 - scale_z
            print("first wall")
            walls.append(Entity(model="cube", collider="box", position=(float(splits[1]), float(splits[2]), float(splits[3])), scale = (float(splits[4]), float(splits[5]), 
                        float(splits[6])), rotation=(0, 0, 0), texture="brick", texture_scale=(5, 5), color=color.rgb(255, 128, 0)))
        elif received.startswith("LOC"):
            splits = received.split("~")
            #split 0 - command, 1 - player, 2 - x, 3 - y, 4 - z, 5 - shooting
            if splits[1] == nickname:
                my_player = FirstPersonController(position = (float(splits[2]), float(splits[3]) + 2, float(splits[4])))
                my_player.cursor.color = color.white
                walking_speed = my_player.speed
            else:
                enemies[splits[1]] = Enemy(splits[1], float(splits[2]), float(splits[3]), float(splits[4]), False, False)

def start():
    global tcp_sock

    Sky()
    window.title = 'My Game'
    window.fullscreen = False
    window.borderless = False

    # getting all the walls' and players' locations
    get_locations()

    #tcp thread
    t = threading.Thread(target=tcp_recv_update)
    t.start()
    threads["tcp"] = t


def main():
    background_sounds["birds_singing"].play()
    app.run()


if __name__ == "__main__":
    start()
    main()
