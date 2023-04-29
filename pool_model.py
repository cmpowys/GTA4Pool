import cv2
import config
from detecto import utils
from conversions import Conversions
import math

class PoolModel(object):
    def __init__(self, model):
        self.model = model
       
    def load_frame(self, screen):
        self.bounding_boxes = self.get_bounding_boxes(screen)
        self.conversions = Conversions.init_from_manual_config()
        self.create_model_space()

    def create_model_space(self):
        self.model_space = dict()
        for label in self.bounding_boxes:
            assert (label in config.ALL_MODEL_LABELS)
            model_space_position = self.conversions.pixel_space_bounding_box_to_model_space(self.bounding_boxes[label])
            self.model_space[label] = model_space_position

    def get_angle_to(self, ball_label):
        assert(not self.bounding_boxes is None)
        assert("white_ball" in self.bounding_boxes)
        assert(ball_label in self.bounding_boxes)

        def middle_of(bounding_box): # repeated calculation refactor
            ((tlx, tly), (brx, bry)) = bounding_box
            return tlx + ((brx - tlx) // 2), tly + ((bry - tly) // 2)    
        
        white_ball_position = middle_of(self.bounding_boxes["white_ball"])
        other_ball_position = middle_of(self.bounding_boxes[ball_label])

        ## this angle calculation is repeated in trajectory.py need to move code somewhere else and improve too
        (x1, y1, x2, y2) = (white_ball_position[0], white_ball_position[1], other_ball_position[0], other_ball_position[1])
        if x2 == x1 or y2 == y1: 
            return 0
        angle = math.atan2((y1 - y2), -(x1 - x2))
        if angle < 0:
            angle += 2*math.pi
        
        return angle

    def predict_image(self, screen):
        filename = config.TEMPORARY_IMAGE_NAME
        cv2.imwrite(filename, screen)
        image = utils.read_image(filename)
        return self.model.predict_top(image)

    def get_bounding_boxes(self, screen):
        labels, boxes, scores  = self.predict_image(screen)

        bounding_boxes = dict()
        for index, label in enumerate(labels):
            assert (label in config.ALL_MODEL_LABELS)
            bounding_box_float = boxes[index]
            bounding_box = ((round(bounding_box_float[0].item()), round(bounding_box_float[1].item())), (round(bounding_box_float[2].item()), round(bounding_box_float[3].item())))
            bounding_boxes[label] = bounding_box

        return bounding_boxes