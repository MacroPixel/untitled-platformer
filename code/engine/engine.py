import os
import pygame
from pygame.locals import RLEACCEL

from .game_object import *
from .vector import *
from .bitmap_font import *

# Abstracts most of the Pygame stuff away
class Engine:

    # Initially set up Pygame & specify global options
    # def __init__( self, size, caption, icon_source = None, fps_limit = -1, root_dir = '' ):
    def __init__( self, size, caption, room_dict, start_room, *args, **kwargs ):

        # Can't be changed for the time being
        self._screen_size = V2( size )

        # Create the window with the desired screen size
        pygame.init()
        pygame.display.set_caption( caption )
        self.__screen = pygame.display.set_mode( self.screen_size.l() )
        self.__clock = pygame.time.Clock()
        self.__fps_clock = pygame.time.Clock()

        # Set the root directory
        # This is where all game resources go, independent of game code
        self.__root_dir = self.dict_search( kwargs, 'root_dir', os.path.dirname( os.getcwd() ) )

        # Set the application icon
        if ( 'icon_source' in kwargs ):
            pygame.display.set_icon( pygame.image.load( self.get_path( kwargs[ 'icon_source' ] ) ) )

        # Remember the max FPS
        self.fps_limit = self.dict_search( kwargs, 'fps_limit', 0 )

        # All sprites are broken into subimages and stored in self.__sprites
        self.__sprites = {}
        self.__load_sprites()

        # All sound objects are stored in self.__sound_paths
        # 32 sounds can be played at once
        pygame.mixer.set_num_channels( 32 )
        self.__sounds = {}
        self.__load_sounds()

        # Holds a reference to every GameObject
        self.__instances = []
        self.__draw_instances = []
        self.__named_instances = {}
        self.__tagged_instances = {}

        # Other variables
        self._delta_time = 0
        self._view_pos = V2()
        self._view_zoom = self.dict_search( kwargs, 'zoom_level', V2( 1, 1 ) )
        self.__keys_down = []
        self.__keys_up = []
        self.__keys = pygame.key.get_pressed()
        self.__fonts = {}
        self.__bitmap_fonts = {}
        self.__zoom_buffer = {}

        # Goto a room
        # This is when the user's code is used
        self.__room_dict = room_dict
        self.load_room( start_room )

    # Enter the main loop
    def run( self ):

        self.__is_running = True
        while self.__is_running:

            # Reset necessary variables
            self._delta_time = min( 0.1, self.__clock.tick() / 1000 )
            self.__keys = pygame.key.get_pressed()
            self.__keys_down = []
            self.__keys_up = []

            # EVENTS
            for event in pygame.event.get():

                # Quit the game
                if event.type == pygame.QUIT:
                    self.__is_running = False

                # Log keypresses
                elif event.type == pygame.KEYDOWN:
                    self.__keys_down.append( event.key )
                elif event.type == pygame.KEYUP:
                    self.__keys_up.append( event.key )

            # update() is called once per frame for all GameObjects
            for obj in self.__instances:
                obj.update()

            # tick() is called 10 times a second for all GameObjects

            # After resetting the draw window, draw() can be called for all GameObjects
            self.__screen.fill( ( 21, 21, 21 ) )
            for obj in self.__draw_instances:
                obj.draw()
            
            # Swap buffers
            pygame.display.update()

            # Limit FPS if necessary
            if ( self.fps_limit > 0 ):
                self.__fps_clock.tick( self.fps_limit )

    # Stores a GameObject for later usage
    def add_instance( self, game_object ):

        # "instances" holds every active GameObject
        self.__instances.append( game_object )

        # "named_instances" allows searching for an object by name
        if game_object.object_id not in self.__named_instances:
            self.__named_instances[ game_object.object_id ] = []
        self.__named_instances[ game_object.object_id ].append( game_object )

        # Tags can be added via "Engine.tag_instance( game_object, tag )"
        game_object._Game_Object__tags = []

        # Insert into proper draw-order-position based on layer
        i = 0
        for i in range( len( self.__draw_instances ) ):
            if self.__draw_instances[i].layer > game_object.layer:
                break
        else:
            i += 1
        self.__draw_instances.insert( i, game_object )

    # Removes a GameObject from memory
    def delete_instance( self, game_object ):

        self.__instances.remove( game_object )
        self.__draw_instances.remove( game_object )
        self.__named_instances[ game_object.object_id ].remove( game_object )

        for tag in game_object._Game_Object__tags:
            self.__tagged_instances[ tag ].remove( game_object )

    # Adds a tag, which marks an object's properties, to an game object
    # Safe to call on objects that already have the tag
    def tag_instance( self, game_object, tag ):

        # "tagged_instances" stores a tag and all the game objects that have it
        # This implementation is very similar to __named_instances
        game_object._Game_Object__tags.append( tag )
        if tag not in self.__tagged_instances:
            self.__tagged_instances[ tag ] = []
        if game_object not in self.__tagged_instances[ tag ]:
            self.__tagged_instances[ tag ].append( game_object )

    # Removes a tag from an instance
    # Safe to call on objects that don't have the tag
    def untag_instance( self, game_object, tag ):

        # "tagged_instances" stores a tag and all the game objects that have it
        # This implementation is very similar to __named_instances
        game_object._GameObject__tags.remove( tag )
        if tag in self.__tagged_instances and game_object in self.__tagged_instances[ tag ]:
            self.__tagged_instances[ tag ].remove( game_object )

    # Gets the state of a key (check of 0 = "is down", 1 = "was pressed", 2 = "was released")
    def get_key( self, key_id, check = 0 ):

        if check == 0:
            return self.__keys[ key_id ]
        elif check == 1:
            return key_id in self.__keys_down
        elif check == 2:
            return key_id in self.__keys_up

    # Initially loads the sprites into memory
    # Should only be called once
    def __load_sprites( self ):

        if ( len( self.__sprites ) != 0 ):
            raise ValueError( 'Sprites have already been initialized' )

        spr_file = open( self.get_path( '/textures/list.txt' ) ).read().split( '\n' )

        # Iterate through every line in the sprite file
        # Sprites are listed as follows:
        # [name] = [relative filepath] [scale]:[# vertical subimages]:[# horizontal subimages]
        for line in spr_file:

            # Parse through the data within the line of text
            internal_name, line = line.split( ' = ' )
            filename, line = line.split( ' ' )
            dimensions = [ int( a ) for a in line.split( ':' ) ]

            # Load the image and transform it based on the data in the file line
            surface = pygame.image.load( self.get_path( '/textures/' + filename ) )
            surface = pygame.transform.scale( surface, V2( surface.get_size() ).l() )

            # Use the dimensions of the sprite divided by the # of subimages to get the size of a square
            dims = V2( surface.get_size() )
            square_count = V2( dimensions )
            square_size = dims.c().d( square_count )

            # Use the previous information to split the sprite up and append it to the sprite data
            self.__sprites[ internal_name ] = [ [ surface.subsurface( ( xx * square_size.x, yy * square_size.y, *square_size.l() ) ) for xx in range( square_count.x ) ]
                for yy in range( square_count.y ) ]

    # Initially loads the sounds into memory
    # Should only be called once
    def __load_sounds( self ):

        if ( len( self.__sounds ) != 0 ):
            raise ValueError( 'Sounds have already been initialized' )

        sound_file = open( self.get_path( '/sounds/list.txt' ) ).read().split( '\n' )

        # Iterate through every line in the sound file
        # Sounds are listed as follows:
        # [name] = [SOUND/MUSIC] [relative filepath] [relative filepath] [relative filepath] [relative filepath] ...
        # Allows multiple filepaths to be specified
        for line in sound_file:

            # Parse through the data within the line of text
            internal_name, line = line.split( ' = ' )
            is_music_str = line.split( ' ' )[0]
            filenames = line.split( ' ' )[1:]

            # Determine if it's a sound or a song
            if ( is_music_str in [ 'SOUND', 'MUSIC' ] ):
                is_music = ( is_music_str == 'MUSIC' )
            else:
                raise ValueError( 'Invalid argument, should be SOUND or MUSIC' )

            # Load all the sound's variants
            sounds = []
            for filename in filenames:
                sounds.append( pygame.mixer.Sound( self.get_path( '/sounds/' + filename ) ) )

            # Append it to the sound data
            self.__sounds[ internal_name ] = sounds

    # Returns a sprite surface for other objects to use
    def get_sprite( self, sprite_id, frame ):

        return self.__sprites[ sprite_id ][ frame.x ][ frame.y ]

    # Drawing methods (preferred over pygame ones because they account for the game view)
    from ._engine_draw import draw_surface
    from ._engine_draw import draw_sprite
    from ._engine_draw import draw_text
    from ._engine_draw import draw_text_bitmap

    # Creates a font under the name 'name:size'
    # Loads it from an external .ttf or .otf file
    def create_font( self, filepath, name, size ):

        self.__fonts[ f'{ name }:{ size }' ] = pygame.font.Font( self.get_path( filepath ), size )

    # Creates a bitmap font from a .PNG
    def create_bitmap_font( self, filepath, name, space_width = None ):

        self.__bitmap_fonts[ name ] = Bitmap_Font( self.get_path( filepath ), space_width = space_width )

    # Sound methods
    from ._engine_mixer import play_sound

    # Appends the input to the root directory
    def get_path( self, directory ):

        return self.__root_dir + directory

    # Returns one or multiple instances of a type
    def get_instance( self, instance_id ):

        if ( instance_id not in self.__named_instances or len( self.__named_instances[ instance_id ] ) == 0 ):
            return None
        return self.__named_instances[ instance_id ][0]

    def get_instances( self, instance_id ):

        if ( instance_id not in self.__named_instances or len( self.__named_instances[ instance_id ] ) == 0 ):
            return []
        return self.__named_instances[ instance_id ]

    # Returns one or multiple instances with a tag
    def get_tagged_instance( self, tag ):

        if ( tag not in self.__tagged_instances or len( self.__tagged_instances[ tag ] ) == 0 ):
            return None
        return self.__tagged_instances[ tag ][0]

    def get_tagged_instances( self, tag ):

        if ( tag not in self.__tagged_instances or len( self.__tagged_instances[ tag ] ) == 0 ):
            return []
        return self.__tagged_instances[ tag ]

    # Loading a room clears all objects and runs a custom function
    # The function is stored in self.__room_dict under a string
    def load_room( self, room_function ):

        # Delete all objects (makes a copy of list so it can be altered during loop)
        for obj in [ o for o in self.__instances ]:
            self.delete_instance( obj )

        # Executes inputted function
        self.__room_dict[ room_function ]( self )

    # Closes the game
    def close_app( self ):

        self.__is_running = False

    # Returns a value from a dictionary if found,
    # otherwise returns the default value passed into the function
    @staticmethod
    def dict_search( dictionary, key, default ):
        
        return dictionary[ key ] if key in dictionary else default

    # Getters and setters
    @property
    def screen_size( self ):
        return self._screen_size.c()

    @property
    def fps_limit( self ):
        return self._fps_limit

    @property
    def fps_current( self ):
        return self.__clock.get_fps()

    @fps_limit.setter
    def fps_limit( self, value ):

        value = int( value )
        if ( value < 0 ):
            raise ValueError( 'FPS limit must be 0 or positive' )
        else:
            self._fps_limit = value

    @property
    def delta_time( self ):
        return self._delta_time

    @property
    def view_pos( self ):
        return self._view_pos

    @view_pos.setter
    def view_pos( self, value ):
        self._view_pos = V2( value )

    @property
    def view_zoom( self ):
        return self._view_zoom.c()

    @view_zoom.setter
    def view_zoom( self, value ):

        # Clear the buffer containing the zoomed in surfaces
        if ( V2( value ).l() != self.view_zoom.l() ):
            self.__zoom_buffer = {}

        # Change the zoom
        self._view_zoom = V2( value )

    @property
    def view_bound_min( self ):

        # Return the top-left of the visible screen in pixel non-screen coordinates
        return self.view_pos.c().s( self.screen_size.d( 2 ).d( self.view_zoom ) )

    @property
    def view_bound_max( self ):

        # Return the bottom-right of the visible screen in pixel non-screen coordinates
        return self.view_pos.c().a( self.screen_size.d( 2 ).d( self.view_zoom ) )