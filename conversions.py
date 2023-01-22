import numpy as np
from numpy.linalg import inv

def array(arr):
    return np.array(arr, dtype=np.float32)

def iarray(arr):
    return np.array(arr, dtype=np.int32)

class Conversions(object):
    def __init__(self, gamespace_topleft, gamespace_bottomleft, gamespace_topright, pixelspace_topleft_bounding_box, pixelspace_bottomleft_bounding_box, pixelspace_topright_bounding_box):
        self.gamespace_topleft = self.gamespace_origin = array(gamespace_topleft)
        self.gamespace_bottomleft = array(gamespace_bottomleft)
        self.gamespace_topright = array(gamespace_topright)
        self.pixelspace_topleft_bounding_box = iarray(pixelspace_topleft_bounding_box)
        self.pixelspace_bottomleft_bounding_box = iarray(pixelspace_bottomleft_bounding_box)
        self.pixelspace_topright_bounding_box = iarray(pixelspace_topright_bounding_box)
        self.set_average_pixelspace_adjustments()
        self.set_pixelspace_delta()
        self.set_modelspace_gamespace_matrices()

    def game_space_to_model_space(self, position):
        return self.gamespace_inverse_basis_matrix  @ (array(position) - self.gamespace_origin)

    def model_space_to_game_space(self, position):
        return (self.gamespace_basis_matrix  @ array(position)) + self.gamespace_origin

    def game_space_to_pixel_space_estimate(self, position):
        return self.model_space_to_pixel_space_estimate(self.game_space_to_model_space(position))

    def model_space_to_pixel_space_estimate(self, position):
        position = array(position)
        return iarray((position * self.pixelspace_delta) + self.middle_of(self.pixelspace_topleft_bounding_box))

    def get_bounding_box_from_point_in_model_space(self, position):
        position = array(position)
        (cx, cy) = self.model_space_to_pixel_space_estimate(position)
        ((tlax, tlay), (brax, bray)) = self.pixelspace_bouding_box_adjustments
        return ((cx + tlax, cy + tlay), (cx + brax, cy + bray))

    def get_bounding_box_from_point_in_game_space(self, position):
        return self.get_bounding_box_from_point_in_model_space(self.game_space_to_model_space(position))

    def pixel_space_to_model_space(self, position):
        position = iarray(position) 
        delta = position - self.middle_of(self.pixelspace_topleft_bounding_box)
        return array((delta[0] / self.pixelspace_delta[0], delta[1] / self.pixelspace_delta[1]))

    def pixel_space_to_game_space(self, position):
        return self.model_space_to_game_space(self.pixel_space_to_model_space(position))

    def set_average_pixelspace_adjustments(self):
        white_ball_bounding_boxes = [self.pixelspace_topleft_bounding_box, self.pixelspace_bottomleft_bounding_box, self.pixelspace_topright_bounding_box]
        count = len(white_ball_bounding_boxes)
        accum = ((0,0), (0, 0))

        for bounding_box in white_ball_bounding_boxes:
            ((tlax, tlay), (brax, bray)) = self.get_pixelspace_adjustment(bounding_box)
            accum = ((accum[0][0] + tlax / count ,accum[0][1] + tlay / count) ,(accum[1][0] + brax / count, accum[1][1] + bray/count))

        self.pixelspace_bouding_box_adjustments = iarray((round(accum[0][0]), round(accum[0][1]))), iarray((round(accum[1][0]), round(accum[1][1])))

    def get_pixelspace_adjustment(self, ball_bounding_box):
        ((tlx, tly), (brx, bry)) = ball_bounding_box
        middle_x, middle_y = self.middle_of(ball_bounding_box)
        tl_adjustment_x = tlx - middle_x
        tl_adjustment_y = tly - middle_y
        br_adjustment_x = brx - middle_x
        br_adjustment_y = bry - middle_y
        return (tl_adjustment_x, tl_adjustment_y), (br_adjustment_x, br_adjustment_y)

    def set_pixelspace_delta(self):
        middle_topleft = self.middle_of(self.pixelspace_topleft_bounding_box)
        middle_bottomleft = self.middle_of(self.pixelspace_bottomleft_bounding_box)
        middle_topright = self.middle_of(self.pixelspace_topright_bounding_box)

        self.pixelspace_delta = iarray((middle_topright[0] - middle_topleft[0], middle_bottomleft[1] - middle_topleft[1]))

    def middle_of(self, bounding_box_pixelspace):
        ((tlx, tly), (brx, bry)) = bounding_box_pixelspace
        return iarray((tlx + round((brx - tlx) / 2), tly + round((bry - tly) / 2)))

    def set_modelspace_gamespace_matrices(self):
        self.gamespace_rightward_basis = self.gamespace_topright - self.gamespace_origin
        self.gamespace_downward_basis = self.gamespace_bottomleft - self.gamespace_origin
        self.gamespace_basis_matrix =  array([[self.gamespace_rightward_basis[0], self.gamespace_downward_basis[0]],[self.gamespace_rightward_basis[1], self.gamespace_downward_basis[1]]])
        self.gamespace_inverse_basis_matrix = inv(self.gamespace_basis_matrix)