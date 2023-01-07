import numpy as np
from numpy.linalg import inv
import manualconfig
import math

def array(arr):
    return np.array(arr, dtype=np.float32)

def iarray(arr):
    return np.array(arr, dtype=np.int32)

gamespace_topleft = gamespace_origin = array(manualconfig.TOPLEFT_CORNER_IN_GAMESPACE)
gamespace_topright = array(manualconfig.TOPRIGHT_CORNER_IN_GAMESPACE)
gamespace_bottomleft = array(manualconfig.BOTTOMLEFT_CORNER_IN_GAMESPACE)
gamespace_bottomright = array(manualconfig.BOTTOMRIGHT_CORNER_IN_GAMESPACE)

pixelspace_pool_ball_bounding_box = iarray(manualconfig.POOL_OBJECT_BOUNDING_BOX_IN_PIXEL_SPACE)

gamespace_rightward_basis = gamespace_topright - gamespace_origin
gamespace_downward_basis = gamespace_bottomleft - gamespace_origin
gamespace_basis_matrix =  array([[gamespace_rightward_basis[0], gamespace_downward_basis[0]],[gamespace_rightward_basis[1], gamespace_downward_basis[1]]])
gamespace_inverse_basis_matrix = inv(gamespace_basis_matrix)

pixelspace_topleft_corner, pixelspace_bottomright_corner = iarray(manualconfig.POOL_TABLE_BOUNDING_BOX_IN_PIXEL_SPACE[0]), iarray(manualconfig.POOL_TABLE_BOUNDING_BOX_IN_PIXEL_SPACE[1])

def game_space_to_model_space(position):
    return gamespace_inverse_basis_matrix  @ (array(position) - gamespace_origin)

def model_space_to_game_space(position):
    return (gamespace_basis_matrix  @ array(position)) + gamespace_origin

def get_bounding_box_from_point_in_model_space(position):
    position = array(position)

    pixelspace_delta = pixelspace_bottomright_corner - pixelspace_topleft_corner
    middle_of_ball = iarray((position * pixelspace_delta) + pixelspace_topleft_corner)

    tlx = pixelspace_pool_ball_bounding_box[0][0]
    tly = pixelspace_pool_ball_bounding_box[0][1]
    brx = pixelspace_pool_ball_bounding_box[1][0]
    bry = pixelspace_pool_ball_bounding_box[1][1]

    diagonal_length = ((brx - tlx)**2 + (bry - tly)**2)**0.5
    radius = math.floor(diagonal_length / 2)
    radius_array = iarray((radius, radius))
    return (middle_of_ball - radius_array, middle_of_ball + radius_array)

def get_bounding_box_from_point_in_game_space(position):
    return get_bounding_box_from_point_in_model_space(game_space_to_model_space(position))