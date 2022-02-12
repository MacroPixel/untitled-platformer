from basic_imports import *
from entity import *

class Box ( Entity ):

    def __init__( self, engine, pos ):

        # Boxes have a 2x2 block hitbox
        super().__init__( engine, 'box', pos, V2(), ( 2, 2, 0, 0 ) )

        # They can also be picked up
        self.entity_item = 'box'
        self.add_tag( 'pickupable' )

    # Shift the box upward when placed down
    def on_drop( self ):

        self.pos.y -= 1

    def draw( self ):

        self.engine.draw_sprite( 'box', V2(), self.pos.c().m( GRID ), False )