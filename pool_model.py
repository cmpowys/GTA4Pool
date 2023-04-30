import cv2
import config
from detecto import utils
from angle_mover import AngleMover ## TODO refactor out common code

class Observation(object):
    def __init__(self, is_solid):
        self.positions = dict()
        self.balls_in_play = dict()
        self.is_solid = is_solid
        
        labels = self.get_labels()

        for label in labels:
            self.balls_in_play[label] = False
            self.positions[label] = (-1.0, -1.0)

    def get_labels(self):
        labels = ["white_ball", "black_ball"]
        solids = [label for label in config.ALL_MODEL_LABELS if "solid" in label]
        stripes = [label for label in config.ALL_MODEL_LABELS if "stripe" in label]

        if self.is_solid:
            labels = labels + solids + stripes
        else:
            labels = labels + stripes + solids

        return labels

    def add_pool_object(self, label, position):
        self.balls_in_play[label] = True
        self.positions[label] = position

    def to_array(self):
        to_return = []
        for label in config.ALL_MODEL_LABELS:
            if "pocket" in label: continue
            x,y = self.positions[label]
            to_return.append(x)
            to_return.append(y)
            to_return.append(int(self.balls_in_play[label]))
        return to_return
    
    

class PoolModel(object):
    def __init__(self, model):
        self.model = model
       
    def load_frame(self, screen, is_solid):
        self.bounding_boxes = self.get_bounding_boxes(screen)
        self.create_observation(is_solid)

    def get_pool_observations(self):
        assert(self.observation is not None)
        return self.observation.to_array()

    def create_observation(self, is_solid):
        self.observation = Observation(is_solid)
        mover = AngleMover(None, None, None)  ## TODO refactor our calculation code
        mover = mover.with_bounding_boxes(self.bounding_boxes)
        for label in self.bounding_boxes:
            assert (label in config.ALL_MODEL_LABELS)
            if not label in self.bounding_boxes: continue
            bounding_box = self.bounding_boxes[label]
            middle = mover.middle_of(bounding_box)
            ((tlx, tly), (brx, bry)) = mover.table_bounding_box
            width = brx - tlx
            height = bry - brx
            ax, ay = mover.adjust_start(middle)
            position = ax / width, ay / height
            self.observation.add_pool_object(label, position)

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