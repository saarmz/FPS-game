from unittest import runner
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import socket, random, time

application.development_mode = False
app = Ursina() # creating a window

ground = Entity(model = "plane", scale = (100, 1, 100), color = color.rgb(0, 255, 25), 
    texture = "grass", texture_scale = (100, 100), collider = "box") # the ground
wall_1 = Entity(model="cube", collider="box", position=(-8, 0, 0), scale = (8, 5, 1), rotation=(0, 0, 0),
    texture="brick", texture_scale=(5, 5), color=color.rgb(255, 128, 0))
wall_2 = duplicate(wall_1, z=5)
wall_3 = duplicate(wall_1, z=10)

my_player = FirstPersonController(y = 2, origin_y = -0.5) # this client's player
walking_speed = my_player.speed

gun = Entity(model="objs/m4", texture = "objs/DiffuseTexture", parent=camera.ui, scale=.13, position = (.42, -.40, -.15),
    rotation=(0, 75, 8))
gun_up = False
running = False
shooting = False
shooting_sounds = {
    "M4_first": Audio("sounds/m4_first.mp3", autoplay=False),
    "M4_shots": Audio("sounds/automat_m4.mp3", autoplay=False),
    "M4_ending": Audio("sounds/m4_ending.mp3", autoplay=False)
    }
last_shot = time.perf_counter()
curr_time = time.perf_counter()
enemies = [] # a list of the other players

def input(key):
    pass


def update():
    """
    Updates values and then renders to screen
    """
    global gun_up, running, shooting, last_shot, curr_time

    #shooting sounds
    if held_keys["left mouse"]:
        curr_time = time.perf_counter()
        if shooting is True and (curr_time - last_shot) >= .148:
            shooting_sounds["M4_shots"].play()
            last_shot = curr_time
        elif shooting is False:
            shooting_sounds["M4_first"].play()
            curr_time = time.perf_counter()
            shooting = True
    elif shooting is True:
        shooting_sounds["M4_ending"].play()
        shooting = False

    #moving the gun while walking    
    if not shooting:
        if held_keys["shift"]:
            running = True
            my_player.speed = 2 * walking_speed
        elif running == True and not held_keys["shift"]:
            my_player.speed = walking_speed
        if held_keys['w'] or held_keys['s'] or held_keys['d'] or held_keys['a']:
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
    else:
        gun.position = (.4, -.40, -.1)
        gun.rotation = (0, 75, 8)
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
    window.title = 'My Game'
    window.fullscreen = True
    window.borderless = False


def main():
    app.run()


if __name__ == "__main__":
    start()
    main()