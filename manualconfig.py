# TODO some of this can be put into config because it never changes
BASE_ADDRESS=0x7E0000 # TODO determine automatically using pymem (better to use ReadWriteMemory but I don't think it supports base address lookup)
POOL_TRIANGLE_IMAGE_AREA = ((877, 483), (1045, 680))
LOCATE_TOPLEFT_BOUND = (1467,45)
LOCATE_BOTTOMRIGHT_BOUND = (1473, 65)


POOL_BALL_POINTERS = {'yellow_solid_ball': '0x87d1db0', 'purple_solid_ball': '0x87d1e00', 'red_solid_ball': '0x87d1ef0', 'blue_solid_ball': '0x87d2fd0', 'black_ball': '0x87d4bf0', 'green_striped_ball': '0x87ca970', 'red_striped_ball': '0x87ca600', 'green_solid_ball': '0x87ca420', 'yellow_striped_ball': '0x87e3fb0', 'orange_solid_ball': '0x87f7ce0', 'blue_striped_ball': '0x87fb340', 'orange_striped_ball': '0x88104c0', 'brown_solid_ball': '0x88107e0', 'purple_striped_ball': '0x8811370', 'brown_striped_ball': '0x8815740'}