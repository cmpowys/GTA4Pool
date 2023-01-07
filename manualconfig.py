# TODO some of this can be put into config because it never changes
BASE_ADDRESS=0x7E0000 # TODO determine automatically using pymem (better to use ReadWriteMemory but I don't think it supports base address lookup)
POOL_BALL_POINTERS = {'brown_striped_ball': '0x806e440', 'green_striped_ball': '0x806e3f0', 'orange_striped_ball': '0x806e3a0', 'purple_striped_ball': '0x806e350', 'red_striped_ball': '0x806e300', 'blue_striped_ball': '0x806e2b0', 'yellow_striped_ball': '0x806e260', 'black_ball': '0x806e210', 'blue_solid_ball': '0x806efd0', 'yellow_solid_ball': '0x806d950', 'purple_solid_ball': '0x806d4f0', 'red_solid_ball': '0x806d310', 'orange_solid_ball': '0x8063310', 'brown_solid_ball': '0x805c240', 'green_solid_ball': '0x800d0f0'}

# The following seem to be consitent enough
POOL_TRIANGLE_BOUNDING_BOX = ((872, 498), (1053, 686))
LOCATE_TOPLEFT_BOUND = (1467,45)
LOCATE_BOTTOMRIGHT_BOUND = (1473, 65)

TOPLEFT_CORNER_IN_GAMESPACE = (1472.734253, 59.65405655)
BOTTOMLEFT_CORNER_IN_GAMESPACE = (1471.322632, 59.48937988)
TOPRIGHT_CORNER_IN_GAMESPACE = (1473.033203,57.07656097)
BOTTOMRIGHT_CORNER_IN_GAMESPACE = (1471.621582,56.91144562)

POOL_OBJECT_BOUNDING_BOX_IN_PIXEL_SPACE = ((901, 572), (926, 599))
POOL_TABLE_BOUNDING_BOX_IN_PIXEL_SPACE = ((153, 308), (1142, 865))

