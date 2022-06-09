from turtle import position
from unittest import runner
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import time, threading, socket, random

application.development_mode = False
app = Ursina() # creating a window

class Bullet(Entity):
    def __init__(self, speed=20, lifetime=10, **kwargs):
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

class Enemy(Button):
    def __init__(self, name, x, y, z) -> None:
        super().__init__(
            parent=scene,
            model="objs/soldier.obj",
            scale=.07,
            position=(x,y,z),
            color = self.color.tint(1),
            highlight_color = self.color.tint(1),
            pressed_color = self.color.tint(1),
            collider = "mesh"
        )
        self.name = name

    def update_loc(self, x, y, z) -> None:
        self.position = (x, y, z)

enemies = {} # a list of the other players



background_sounds = {
    "birds_singing": Audio("sounds/birds.mp3", autoplay=True, loop=True, volume=.3)
}

my_player = FirstPersonController(y = 6, origin_y = -0.5) # this client's player
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
    
def muzzle_flash(entity):
    pass

def shoot_check_hit():
    global enemies

    Bullet(model="sphere", color=color.gold, scale=1, position=my_player.camera_pivot.world_position,
    rotation=my_player.camera_pivot.world_rotation)
    for enemy in enemies:
        if enemies[enemy].hovered:
            destroy(enemies[enemy])
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
            muzzle_flash(camera.ui)
            mag_size.text = f"mag: {mag}"
        else:
            curr_time = time.perf_counter()
            if curr_time - last_shot >= .085:
                mag -= 1
                shoot_check_hit()
                muzzle_flash(camera.ui)
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
    global gun_up, running, moving

    shooting_sounds()
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


def login():
    """
    Performs secure TCP log in process
    """
    pass

def start():
    login()
    Sky()
    ground = Entity(model = "plane", scale = (100, 1, 100), color = color.rgb(0, 255, 25), 
    texture = "grass", texture_scale = (100, 100), collider = "box") # the ground
    wall_1 = Entity(model="cube", collider="box", position=(-8, 0, 0), scale = (8, 5, 1), rotation=(0, 0, 0),
        texture="brick", texture_scale=(5, 5), color=color.rgb(255, 128, 0))
    wall_2 = duplicate(wall_1, z=5)
    wall_3 = duplicate(wall_1, z=10)
    window.title = 'My Game'
    window.fullscreen = True
    window.borderless = True

    enemies["Mike"] = Enemy("Mike", 25, 0, 7)
    enemies["John"] = Enemy("John", 8,  0, 5)
    enemies["Willy"] = Enemy("Willy", 14, 0, 3)
    enemies["Bob"] = Enemy("Bob", 5,  0, -9)


def main():
    app.run()


if __name__ == "__main__":
    start()
    main()