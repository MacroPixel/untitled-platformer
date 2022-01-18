import pygame
from math import floor, ceil, sin, cos
import random
from engine import *
from constants import *

# Controls basic game logic
# Other controller objects exist for more specific game logic
class Controller( GameObject ):

  def __init__( self, engine ):

    # Create fonts
    super().create_instance()
    engine.create_font( 'res/misc/font_1.otf', 'main', 20 )
    engine.create_font( 'res/misc/font_1.otf', 'main', 12 )

    # Debug mode can be toggled with right alt
    self.allow_debug = True
    self.debug = True

  # Mostly just debug stuff
  def update( self, engine ):

    # Switch debug mode if allowed
    if engine.get_key( pygame.K_RALT, 1 ):
      self.debug = not self.debug

    # Debug features
    if self.debug:
      
      # Restart
      if ( engine.get_key( pygame.K_r, 1 ) ):
        self.restart( self.get_instance( 'player' ) )

      # Reload level
      if ( engine.get_key( pygame.K_l, 1 ) ):
        c_block.load_level()

      # Rewrite level
      if ( engine.get_key( pygame.K_k, 1 ) ):
        c_block.rewrite_level()

  # Reset the player & reload blocks
  def restart( self, player ):

    player.pos = V2( 0, 0 )
    player.vel = V2( 0, 0 )

# Handles UI drawing & responses
class UIController( GameObject ):

  def __init__( self ):

    # State represents the UI menu
    super().create_instance( layer = -1000 )
    self.state = [ 1 ]

  def draw( self, engine ):

    if self.state[0] == 1:
      engine.draw_text( '[ESC] Pause', 'main:20', V2( 20, 20 ), ( 255, 255, 255 ) )

    if c_main.debug:
      engine.draw_text( 'Debug', 'main:12', engine.screen_size.c().s( 10, 10 ), ( 0, 100, 255 ), V2( 1, 1 ) )

# Handles block storing/drawing
# Blocks aren't actually objects, they're only entries in an array
class BlockController( GameObject ):

  # Maps a string to an enum block type
  enum_values = {
    'default': B_DEFAULT,
    'goop': B_GOOP,
    'leaf': B_LEAF,
    'wood': B_WOOD,
    'lava': B_LAVA,
    'cloud': B_CLOUD
  }

  def __init__( self ):

    super().create_instance( layer = 0 )

    # Block data
    self.blocks = {}
    self.block_meta = {}
    self.chunks = {}
    self.chunk_buffers = {}
    self.loaded_chunks = []

    # Surface data (switches between the two)
    self.buffer_a = None

    # Initialize block data
    self.load_level()

  # Loads the level data into memory
  def load_level( self ):

    level_data = open( 'res/data/blocks.txt' ).read().split( '\n' )

    # Group the data into chunks (denoted by "* X:Y")
    # This is done solely to aid with drawing the blocks in
    self.blocks = {}
    self.chunks = {}
    self.chunk_buffers = {}
    self.loaded_chunks = []
    current_chunk = ''
    for line in level_data:

      # Switch chunk
      if len( line ) == 0:
        pass

      elif line[0] == '*':
        current_chunk = line.split( '* ' )[1].split( ':' )
        try:
          current_chunk = f'{ int( current_chunk[0] ) }:{ int( current_chunk[1] ) }'
          self.chunks[ current_chunk ] = []
        except ( ValueError, IndexError ):
          raise GameError( 'Invalid chunk format' )

      # Create objects under chunk
      else:

        # If chunk isn't active
        if ( current_chunk == '' ):
          raise GameError( 'No chunk was specified' )

        # Otherwise, store the block name & loop through coordinates
        block_name = self.enum_values[ line.split( ' ' )[0] ]
        for i in range( 1, len( line.split( ' ' ) ), 2 ):

          # Create block & store position under current chunk
          temp_pos = V2( line.split( ' ' )[ i:i + 2 ] ).i().a( str_to_vec( current_chunk ).m( C_GRID ) )
          self.set_block( temp_pos, block_name )
          self.chunks[ current_chunk ].append( vec_to_str( temp_pos ) )

  # Recreates the level data from a PNG image
  def rewrite_level( self ):

    # Load the PNG into memory
    block_surf = pygame.image.load( 'res/data/blocks.png' )

    keys = {} # The position of every block in the PNG
    origin = V2( 0, 0 ) # Where the player spawns

    # Loop through all the pixels in the PNG
    for xx in range( block_surf.get_width() ):
      for yy in range( block_surf.get_height() ):

        pos = V2( xx, yy )

        # Create the player if the pixel is white
        if block_surf.get_at( pos.l() ) == ( 255, 255, 255, 255 ):
          origin = pos

        # Otherwise, create the appropriate block based on color
        else:
          for i in range( 1, B_TOTAL ):
            if block_surf.get_at( pos.l() ) == B_COLORS[ i ]:
              keys[ vec_to_str( pos ) ] = i

    # Store the real position of every block,
    # relative to the origin instead of top-left of image
    chunks = {}

    for pos in keys:

      new_pos = str_to_vec( pos ).s( origin )
      chunk_pos = new_pos.c().d( C_GRID ).fn( lambda a: int( floor( a ) ) )
      chunk_str = vec_to_str( chunk_pos )

      if chunk_str not in chunks:
        chunks[ chunk_str ] = {}
      chunks[ chunk_str ][ vec_to_str( new_pos.c().s( chunk_pos.c().m( C_GRID ) ) ) ] = keys[ pos ]

    # Actually write to the file
    file = open( 'res/data/blocks.txt', 'w' )
    for chunk in chunks:

      file.write( f'* { chunk }\n' )

      for block_pos in chunks[ chunk ]:
        file.write( f'{ key_value( self.enum_values, chunks[ chunk ][ block_pos ] ) } { block_pos.replace( ":", " " ) }\n' )
      
  # Iterate through/draw all blocks
  # Blocks are drawn based off of chunk buffers stored in memory
  def draw( self, engine ):

    # Draw chunks within the proper bound
    bound_1 = engine.view_pos.c().s( RENDER_BOUNDS * GRID ).fn( lambda a: floor( a / GRID / C_GRID ) )
    bound_2 = engine.view_pos.c().a( engine.screen_size ).a( RENDER_BOUNDS * GRID ).fn( lambda a: floor( a / GRID / C_GRID ) )
    for xx in range( bound_1.x, bound_2.x + 1 ):
      for yy in range( bound_1.y, bound_2.y + 1 ):

        chunk_pos = V2( xx, yy )

        # Make sure the chunk exists
        if vec_to_str( chunk_pos ) not in self.chunks:
          continue

        # Create the chunk if it doesn't exist
        if ( vec_to_str( chunk_pos ) not in self.chunk_buffers ):
          self.load_chunk( chunk_pos, engine )

        engine.draw_surface( self.chunk_buffers[ vec_to_str( chunk_pos ) ], chunk_pos.c().m( C_GRID * GRID ) )

  # Creates a surface for easy-drawing
  # I've decided to postpone implementing this until there's enough blocks for it to make a difference
  def load_chunk( self, chunk_pos, engine ):
    
    # Initialize it with an empty surface
    surf = pygame.Surface( ( C_GRID * GRID, C_GRID * GRID ) )
    self.chunk_buffers[ vec_to_str( chunk_pos ) ] = surf

    # Draw every block onto it
    for xx in range( C_GRID ):
      for yy in range( C_GRID ):
        
        block_pos = chunk_pos.c().m( C_GRID ).a( xx, yy )

        if ( c_block.is_block( block_pos ) ):
          surf.blit( self.render_block( block_pos, engine ), ( xx * GRID, yy * GRID ) )

  # Returns either None or a surface representing a block sprite
  def render_block( self, block_pos, engine ):

    if self.is_block( block_pos ):
      return engine.get_image( B_TEXTURES[ self.blocks[ vec_to_str( block_pos ) ] ], V2( 0, 0 ) )
    else:
      return None

  # Either changes a block or removes it (by setting it to B_NULL)
  def set_block( self, pos, block_type ):

    # Convert position & alter array
    pos = V2( pos )
    if block_type == B_NULL:
      self.blocks.pop( vec_to_str( pos ) )
      self.block_meta.pop( vec_to_str( pos ) )
    else:

      # Initialize the block data
      self.blocks[ vec_to_str( pos ) ] = block_type
      self.block_meta[ vec_to_str( pos ) ] = {}

      # Do any further setup
      if ( B_DRAW_MODES[ block_type ] in [ BDM_DEF_OVERLAY, BDM_DEF_REPLACE, BDM_DEF_OUTLINE ] ):
        self.block_meta[ vec_to_str( pos ) ][ 'var' ] = random.randint( 0, 2 )
      else:
        self.block_meta[ vec_to_str( pos ) ][ 'var' ] = 0

  # Check whether a block exists at a position
  def is_block( self, pos ):

    return vec_to_str( pos ) in self.blocks

  # Get the block type of a position
  # !!! WILL throw error if there isn't a block there
  def get_block_type( self, pos ):

    return self.blocks[ f'{ pos.x }:{ pos.y }' ]

# It's you :D
class Player ( GameObject ):

  def __init__( self ):

    # Store image & physics details
    super().create_instance( obj = 'player' )
    self.image_dir = 1
    self.image_walk = 0
    self.image_bob = 0
    self.pos = V2()
    self.vel = V2()

  def update( self, engine ):
    
    # Horizontal movement
    if engine.get_key( pygame.K_d ):
      self.vel.x += PLAYER_HSPEED * engine.delta_time
    elif engine.get_key( pygame.K_a ):
      self.vel.x -= PLAYER_HSPEED * engine.delta_time
    elif self.is_on_block():
      self.vel.x *= ( 1 / PLAYER_FRICTION ) ** engine.delta_time

    # Vertical movement
    if ( self.is_on_block() or c_main.debug ) and engine.get_key( pygame.K_SPACE ):

      # Jump
      self.vel.y = -PLAYER_JUMP_POWER

      # Jumping also gives a boost to horizontal speed
      if self.is_on_block() and engine.get_key( pygame.K_d ):
        self.vel.x += PLAYER_HSPEED_BOOST
      elif self.is_on_block() and engine.get_key( pygame.K_a ):
        self.vel.x -= PLAYER_HSPEED_BOOST

    self.vel.y += GRAVITY * engine.delta_time

    self.image_walk += abs( self.vel.x ) * engine.delta_time * 3

    # Set image details
    # Walk is incremented while velocity >= 0.2, otherwise head bob is incremented
    if abs( self.vel.x ) < 0.5:
      self.image_walk = 0
    if abs( self.vel.x ) < 0.5 and self.is_on_block():
      self.image_bob += engine.delta_time * 0.8
    else:
      self.image_bob = 0
    if ( self.vel.x ) < -0.01:
      self.image_dir = -1
    elif ( self.vel.x > 0.01 ):
      self.image_dir = 1

    # Actually move
    # Perform collision detection on the 4 adjacent blocks
    # This is done with multiple iterations to make it more precise
    vel_factor = V2( 1, 1 )

    iterations = 5
    for i in range( iterations ):

      self.pos.x += self.vel.x * engine.delta_time / iterations
      self.push_out( is_x_axis = True )

      self.pos.y += self.vel.y * engine.delta_time / iterations
      self.push_out( is_x_axis = False )

    # Update view
    # if ( self.pos.x * GRID + GRID / 2 < engine.view_pos.x + engine.screen_size.x / 2 - VIEW_BOUNDS[0] ):
    #   engine.view_pos.x = self.pos.x * GRID - engine.screen_size.x / 2 + VIEW_BOUNDS[0]
    engine.view_pos = V2( self.pos.x * GRID - engine.screen_size.x / 2, self.pos.y * GRID - engine.screen_size.y / 2 ).i()

  # Draw self at current position
  # Leverages flip operations & sub-images
  def draw( self, engine ):

    if abs( self.vel.x ) < 0.5:
      engine.draw_image_mod( 'player', V2( 0, floor( self.image_bob ) % 2 ), self.pos.c().m( GRID ), flip = V2( self.image_dir, 1 ) )
    else:
      engine.draw_image_mod( 'player', V2( 1, floor( self.image_walk ) % 8 ), self.pos.c().m( GRID ), flip = V2( self.image_dir, 1 ) )

  # Checks if the player has a block immediately (to a limited degree) below them
  def is_on_block( self ):

    return ( c_block.is_block( V2( int( floor( self.pos.x ) ), int( floor( self.pos.y + 1 ) ) ) )
      or c_block.is_block( V2( int( ceil( self.pos.x ) ), int( floor( self.pos.y + 1 ) ) ) ) )

  # Returns a list of the vectors of any blocks the player is inside of
  def get_adjacent_blocks( self, position = None ):

    if position == None:
      position = self.pos
    output = []
    for xx in range( floor( position.x ), ceil( position.x ) + 1 ):
      for yy in range( floor( position.y ), ceil( position.y ) + 1 ):    
        output.append( V2( xx, yy ) )
    return output

  # Push the player out of any adjacent blocks
  def push_out( self, is_x_axis ):

    adjacent_blocks = self.get_adjacent_blocks()

    # For every grid space the player is inside of
    for block_pos in adjacent_blocks:

      # Only continue if a block occupies this grid space
      if ( not c_block.is_block( block_pos ) ):
        continue

      # Push the player out based on their position within the block
      # The is_x_axis argument determines the axis they're pushed along
      if ( is_x_axis ):
        self.pos.x = block_pos.x + ( -1 if self.pos.x < block_pos.x else 1 )
        self.vel.x = 0
      else:
        self.pos.y = block_pos.y + ( -1 if self.pos.y < block_pos.y else 1 )
        self.vel.y = 0

# Vector / string transformation
def vec_to_str( value ):
  return ':'.join( value.c().fn( lambda a: str( a ) ).l() )

def str_to_vec( value ):
  return V2( value.split( ':' ) ).i()

# I know global objects are considered bad practice, but I don't really care.
g_engine = Engine( V2( 1280, 720 ), 'Untitled Platformer', icon_source = 'res/textures/icon.png', fps_limit = -1 )
c_main = Controller( g_engine )
c_ui = UIController()
c_block = BlockController()

Player()

g_engine.run()