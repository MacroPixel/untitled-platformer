from basic_imports import *
from entity import *

# It's you :D
class Player ( Entity ):

    def __init__( self, engine ):

        super().__init__( engine, 'player', V2(), V2(), V2( PLAYER_HITBOX ) )
        self.entity_destroy_on_death = False

        # Store image & physics details
        self._image_dir = 1
        self._image_walk = 0
        self._image_bob = 0
        self._image_attack = 0

        # Other variables
        self._is_alive = True

        # Debug variables
        self._is_invulnerable = False

    def update( self ):

        # Cancel if game is paused
        if ( self.engine.get_instance( 'controller' ).pause_level >= PAUSE_NORMAL ):
            return

        # Only move if player is alive
        if ( self.is_alive ):
            self.update_normal()

        # Update view regardless
        self.engine.view_pos.x = utils.lerp( self.engine.view_pos.x, self.pos.x * GRID, 0.85, self.engine.delta_time * 10 )
        self.engine.view_pos.y = utils.lerp( self.engine.view_pos.y, self.pos.y * GRID, 0.85, self.engine.delta_time * 10 )
        self.engine.view_pos.fn( lambda a: round( a, 2 ) )

    # Actions to perform every frame if game is unpaused
    def update_normal( self ):
        
        # Horizontal momentum
        # PLAYER_HSPEED defines the base speed
        # The player experiences a deficit of momentum when they're not standing on a block
        # This is defined as PLAYER_HSPEED_AIR_FACTOR
        # Friction (only when on block) works by pretending they're holding the key
        # in the opposite direction they're moving
        velocity_factor = 1
        if ( not self.is_on_block() ):
            velocity_factor *= PLAYER_HSPEED_AIR_FACTOR
        if ( self.engine.get_key( BINDS[ 'move_right' ] ) ):
            self.vel.x += PLAYER_HSPEED * self.engine.delta_time * velocity_factor
        elif ( self.engine.get_key( BINDS[ 'move_left' ] ) ):
            self.vel.x -= PLAYER_HSPEED * self.engine.delta_time * velocity_factor
        elif self.is_on_block():
            self.vel.x = max( abs( self.vel.x ) - ( PLAYER_HSPEED * self.engine.delta_time * velocity_factor ), 0 ) * ( -1 if self.vel.x < 0 else 1 )

        # Vertical momentum
        can_jump = ( self.is_on_block() and self.engine.get_key( BINDS[ 'jump' ] ) )
        if ( can_jump ):

            # Jump
            self.vel.y = -PLAYER_JUMP_POWER

            # Jumping also gives a boost to horizontal speed
            if self.is_on_block() and self.engine.get_key( BINDS[ 'move_right' ] ):
                self.vel.x += PLAYER_HSPEED_BOOST
            elif self.is_on_block() and self.engine.get_key( BINDS[ 'move_left' ] ):
                self.vel.x -= PLAYER_HSPEED_BOOST

        # Abilities
        if ( self.engine.get_key( BINDS[ 'attack' ], 1 ) ):
            self.attack()

        if ( self.engine.get_key( BINDS[ 'invert' ], 1 ) ):
            self.invert()

        # Damage
        if ( self.engine.get_key( pygame.K_n, 1 ) ):
            self.die()

        # Set image details
        # Walk is incremented while velocity >= 0.2, otherwise head bob is incremented
        self._image_walk += abs( self.vel.x ) * self.engine.delta_time * 3
        if abs( self.vel.x ) < 0.5:
            self._image_walk = 0
        if abs( self.vel.x ) < 0.5 and self.is_on_block():
            self._image_bob += self.engine.delta_time * 0.8
        else:
            self._image_bob = 0
        if ( self.vel.x ) < -0.01:
            self._image_dir = -1
        elif ( self.vel.x > 0.01 ):
            self._image_dir = 1

        # If attack is > 0, it goes through 1 frame every 0.05 seconds
        if ( self.image_attack > 0 ):
            self._image_attack = max( 0, self._image_attack - self.engine.delta_time / 0.05 )

        # Actually move
        # Perform collision detection on the 4 adjacent blocks
        # This is done with multiple iterations to make it more precise
        vel_factor = V2( 1, 1 )

        Entity.entity_update( self )

    # ABILITIES

    def attack( self ):

        # Comes at a cost of velocity
        self.vel.x *= PLAYER_HSPEED_ATTACK_FACTOR
        self.engine.play_sound( 'punch' )

        # Play attack animation
        self._image_attack = 3

    # Rotates velocity vector 90 degrees counterclockwise
    def invert( self ):

        self.vel.x, self.vel.y = self.vel.y, -self.vel.x

    # OTHER BEHAVIOR

    # Creates an object that displays UI and eventually restarts the level
    def die( self ):

        # Only die if vulnerable
        if ( not self.is_invulnerable ):
            self._is_alive = False
            super().die()

    # Draw self at current position
    # Leverages flip operations & sub-images
    # Also drawn slightly higher than the player's position because its hitbox isn't centered
    def draw( self ):

        # TODO: fit hitbox precision error leading to player being drawn in ground

        # Don't draw unless alive
        if ( not self.is_alive ):
            return

        hitbox_offset = V2( 0, ( 1 - PLAYER_HITBOX[1] ) / 2 )
        draw_pos = self.pos.c().s( hitbox_offset ).m( GRID )

        if ( self._image_attack > 0 ):
            draw_image = V2( 2, min( 2, 2 - floor( self.image_attack ) ) )
        elif abs( self.vel.x ) < 0.5:
            draw_image = V2( 0, floor( self.image_bob ) % 2 )
        else:
            draw_image = V2( 1, floor( self.image_walk ) % 8 )

        self.engine.draw_sprite( 'player', draw_image, draw_pos.c(), False, flip = V2( self.image_dir, 1 ) )

        # Store the sprite for usage in ragdoll
        self.update_ragdoll( 'player', draw_pos.c().d( GRID ), self.image_dir == -1 )

    # Checks if the player has a block immediately (to a limited degree) below them
    def is_on_block( self ):

        controller = self.engine.get_instance( 'controller' )
        for xx in range( floor( self.pos.x + ( 1 - PLAYER_HITBOX[0] ) / 2 + COLLISION_EPSILON ), ceil( self.pos.x + ( 1 + PLAYER_HITBOX[0] ) / 2 - COLLISION_EPSILON ) ):
            if ( controller.is_solid( V2( xx, int( floor( self.pos.y + ( 1 + PLAYER_HITBOX[1] ) / 2 ) ) ) ) ):
                return True
        return False

    # Resets all properties after level restart
    def restart( self ):

        self.pos = V2( 0, 0 )
        self.vel = V2( 0, 0 )
        self._is_alive = True

    @property
    def image_dir( self ):
        return self._image_dir

    @property
    def image_walk( self ):
        return self._image_walk

    @property
    def image_attack( self ):
        return self._image_attack

    @property
    def image_bob( self ):
        return self._image_bob

    @property
    def is_alive( self ):
        return self._is_alive

    @property
    def is_invulnerable( self ):
        return self._is_invulnerable