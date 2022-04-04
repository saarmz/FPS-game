from unittest import runner
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import socket, random

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

gun = Entity(model="objs/m4", texture = "objs/DiffuseTexture", parent=camera.ui, scale=.13, position = (.4, -.40, -.1),
    rotation=(0, 75, 8))
gun_up = False

running = False

enemies = [] # a list of the other players


def update():
    """
    Updates values and then renders to screen
    """
    global gun_up, running
    #moving the gun while walking
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