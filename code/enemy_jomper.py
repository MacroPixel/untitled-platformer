from basic_imports import *
from enemy import *

class Jomper ( Enemy ):

    def __init__( self, engine, pos ):

        super().__init__( engine, 'jomper', pos, V2(), V2( 1, 1 ) )

    def update( self ):

        # Cancel if game is paused
        if ( self.engine.get_instance( 'controller' ).pause_level >= PAUSE_NORMAL ):
            return

        # Vertical movement (gravity only)
        self.vel.y += GRAVITY * self.engine.delta_time

        # Actually move
        Entity.entity_update( self, iterations = 1 )

    def draw( self ):

        draw_pos = self.pos.c().m( GRID )
        self.engine.draw_sprite( 'jomper', V2( 0, 0 ), draw_pos, False )

        self.update_ragdoll( 'jomper', self.pos.c(), self.vel.x < 0, V2( 0.5, 0.65 ) )