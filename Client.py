from msilib.schema import Billboard
from operator import truediv
from pickle import FALSE
from pydoc import visiblename
from turtle import position
from unittest import runner
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import time, threading, socket
from random import randint

# Global variables used for setting up connection
tcp_sock = socket.socket()
PORT = 9321
key = 0
nickname = ""

def recv(sock):
    byte_data = sock.recv(1024)
    if byte_data == b'':
        return ""
    else:
        return byte_data.decode("utf-8")

def diffie_hellman(sock):
    global key

    n = 1008001 # relatively large prime number
    g = 151 # small prime number
    a = random.randint(0, n)

    bg = int(sock.recv(2048).decode("utf-8"))
    ag = (g**a) % n
    sock.send(f"{str(ag)}".encode("utf-8"))

    key = (bg**a) % n

def menu():
    """
    Takes care of start menu before the game begins
    """
    global server_ip, nickname

    connected = False
    #TODO: change it back to input
    server_ip = "192.168.1.245"
    try:
        tcp_sock.connect((server_ip, PORT))
        print(f'Connect succeeded {server_ip}:{PORT}')
        connected = True
    except:
        print(f'Error while trying to connect.  Check ip or port -- {server_ip}:{PORT}')
        return False
    
    if connected:
        diffie_hellman(tcp_sock)
        nickname = "Saar"
        inp = "T"
        if inp == "T":
            lobby = "lob"
            password = "pas"
            message = f"NEW~{nickname}~{lobby}~{password}"
            tcp_sock.send(message.encode("utf-8"))

            input("Press ENTER when everyone's ready to start the game")
            tcp_sock.send(f"READY~{nickname}~{lobby}~{password}".encode("utf-8"))
            print(recv(tcp_sock))
            #TODO: wait for everyone's and everything's locations
        else:
            name = input("Please enter the lobby's name: ")
            password = input("Please enter the lobby's password: ")
            message = f"JOIN~{nickname}~{name}~{password}"
            tcp_sock.send(message.encode("utf-8"))


        return True

start = menu()
if not start:
    sys.exit()
application.development_mode = False
app = Ursina() # creating a window

class Bullet(Entity):
    def __init__(self, speed=20, lifetime=5, **kwargs):
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
    def __init__(self, name, x, y, z, shooting) -> None:
        if shooting:
            self.animation = FrameAnimation3d("shooting_walking/shooting", scale=0.073, position=(x, y, z), autoplay=False)
            self.obj = Entity(model="shooting_walking/shooting1.obj", parent=self.animation, collider="mesh", visible=False)
            self.muzzle_animation = Animation("objs/muzzle_flash.gif", parent=self.animation, y=24, z=24, scale=22, billboard=True)
        else:
            self.animation = FrameAnimation3d("soldier_walking/soldier", scale=0.073, position=(x, y, z), autoplay=False)
            self.obj = Entity(model="soldier_walking/soldier1.obj", parent=self.animation, collider="mesh", visible=False)
            self.muzzle_animation = False
        self.name = name
        self.walking = False
        self.last_walk = 0
        self.speed = 0.3
        self.shooting = shooting
        # txt = Text(text=name, parent=self.animation, billboard=True)

    def update(self):
        if self.walking:
            curr_time = time.perf_counter()
            if curr_time - self.last_walk >= 0.01:
                self.animation.position += self.obj.forward * self.speed
                self.last_walk = curr_time

    def update_loc(self, x, y, z) -> None:
        self.position = (x, y, z)
    
    def update_rotation(self, rotation) -> None:
        self.animation.rotation = rotation
    
    def update_walk(self, to_walk) -> None:
        if to_walk and not self.walking:
            self.walking = True
            self.animation.start()
        elif not to_walk and self.walking:
            self.walking = False
            self.animation.pause()
    
    def update_shooting(self, shoot):
        if shoot and not self.shooting:
            pos = self.animation.position
            destroy(self.animation)
            destroy(self.obj)
            destroy(self.muzzle_animation)
            self.animation = FrameAnimation3d("shooting_walking/shooting", scale=0.073, position=pos, autoplay=False)
            self.obj = Entity(model="shooting_walking/shooting1.obj", parent=self.animation, collider="mesh", visible=False)
            self.muzzle_animation = Animation("objs/muzzle_flash.gif", parent=self.animation, y=24, z=24, scale=22, billboard=True)
        elif not shoot and self.shooting:
            pos = self.animation.position
            destroy(self.animation)
            destroy(self.obj)
            destroy(self.muzzle_animation)
            self.animation = FrameAnimation3d("soldier_walking/soldier", scale=0.073, position=pos, autoplay=False)
            self.obj = Entity(model="soldier_walking/soldier1.obj", parent=self.animation, collider="mesh", visible=False)
            self.muzzle_animation = False


# Global variables used for the game
enemies = {} # a dictionary of the other players

background_sounds = {
    "birds_singing": Audio("sounds/birds.mp3", autoplay=False, loop=True, volume=.3)
}

ground = Entity(model = "plane", scale = (100, 1, 100), color = color.rgb(0, 255, 25), 
                texture = "grass", texture_scale = (100, 100), collider = "box") # the ground
my_player = FirstPersonController(position = (0, 2, 0)) # this client's player
my_player.cursor.color = color.white
walking_speed = my_player.speed

gun = Entity(model="objs/m4", texture = "objs/DiffuseTexture", parent=camera.ui, scale=.13, position = (.42, -.40, -.15),
            rotation=(0, 75, 8))
gun_up = False
moving = False
running = False
shooting = False
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
last_shot = time.perf_counter()
curr_time = time.perf_counter()


def input(key):
    global mag, mag_size
    if key == 'r':
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
    global enemies

    Bullet(model="sphere", color=color.gold, scale=1, position=my_player.camera_pivot.world_position,
            rotation=my_player.camera_pivot.world_rotation)
    if len(enemies) > 0:
        for enemy in enemies:
            if enemies[enemy].obj.hovered:
                destroy(enemies[enemy].obj)
                destroy(enemies[enemy].animation)
                enemies.pop(enemy)
                break


def shooting_sounds():
    global mag, shooting, last_shot, curr_time, mag_size, m4_sounds
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

def update():
    """
    Updates values and then renders to screen
    """
    global gun_up, running, moving, enemies

    shooting_sounds()

    #TODO: make players' names visible

    #moving the gun while walking    
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

def start():
    Sky()
    wall_1 = Entity(model="cube", collider="box", position=(-8, 0, 0), scale = (8, 5, 1), rotation=(0, 0, 0),
                    texture="brick", texture_scale=(5, 5), color=color.rgb(255, 128, 0))
    wall_2 = duplicate(wall_1, z=5)
    wall_3 = duplicate(wall_1, z=10)
    window.title = 'My Game'
    window.fullscreen = True
    window.borderless = True

    #Creating the enemies
    enemies["Bob"] = Enemy("Bob", 8, 0, 0, True)
    enemies["Willy"] = Enemy("Willy", 6,  0, 0, False)
    enemies["John"] = Enemy("John", 4, 0, 0, True)
    enemies["Mike"] = Enemy("Mike", 2,  0, 0, False)

    enemies["Mike"].update_walk(True)
    enemies["John"].update_walk(True)
    enemies["John"].update_rotation(Vec3(enemies["John"].animation.rotation_x, enemies["John"].animation.rotation_y+40, enemies["John"].animation.rotation_z))


def main():
    background_sounds["birds_singing"].play()
    app.run()


if __name__ == "__main__":
    start()
    main()
