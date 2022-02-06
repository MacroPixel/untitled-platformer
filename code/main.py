import os
os.environ[ 'PYGAME_HIDE_SUPPORT_PROMPT' ] = ''
import pygame
from math import floor, ceil, sin, cos
import random

from engine.engine import *
from constants import *
from rooms import *

def main():

    g_engine = Engine( V2( 1280, 720 ), 'Untitled Platformer',
        room_dict = ROOM_DICT,
        start_room = 'frontend',
        root_dir = os.path.dirname( os.getcwd() ) + '/res',
        icon_source = '/textures/icon.png',
        fps_limit = 0,
        zoom_level = V2( 3, 3 )
    )
    g_engine.run()

if __name__ == '__main__':

    main()