import cv2
import config
from detecto import utils
from angle_mover import AngleMover ## TODO refactor out common code
from pool_state import CurrentPoolType

THRESHOLD = 0.5

class Observation(object):
    def __init__(self, current_pool_type):
        self.positions = dict()
        self.balls_in_play = dict()
        self.current_pool_type = current_pool_type
        
        labels = self.get_labels()

        for label in labels:
            self.balls_in_play[label] = 0.0
            self.positions[label] = (-1.0, -1.0)

    def get_labels(self):
        labels = ["white_ball", "black_ball"]
        solids = [label for label in config.ALL_MODEL_LABELS if "solid" in label]
        stripes = [label for label in config.ALL_MODEL_LABELS if "stripe" in label]

        #if self.is_solid:
        labels = labels + solids + stripes
        #else:
            #labels = labels + stripes + solids

        return labels

    def add_pool_object(self, label, position, score):
        if score >= THRESHOLD:
            self.balls_in_play[label] = 1.0
            self.positions[label] = position

    def to_array(self):
        to_return = []
        player = 0.0
        if self.current_pool_type == CurrentPoolType.SOLID:
            player = -1.0
        elif self.current_pool_type == CurrentPoolType.STRIPES:
            player = 1.0
        to_return.append(player)
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
       
    def load_frame(self, screen, current_pool_type):
        self.bounding_boxes = self.get_bounding_boxes(screen)
        self.create_observation(current_pool_type)

    def get_pool_observations(self):
        assert(self.observation is not None)
        return self.observation.to_array()

    def create_observation(self, current_pool_type):
        self.observation = Observation(current_pool_type)
        mover = AngleMover(None, None, None)  ## TODO refactor our calculation code
        mover = mover.with_bounding_boxes(self.bounding_boxes)
        for label in self.bounding_boxes:
            assert (label in config.ALL_MODEL_LABELS)
            if not label in self.bounding_boxes: continue
            bounding_box = self.bounding_boxes[label]
            middle = mover.middle_of(bounding_box)
            ((tlx, tly), (brx, bry)) = mover.table_bounding_box
            width = brx - tlx
            height = bry - tly
            ax, ay = mover.adjust_start(middle)
            position = ax / width, ay / height
            self.observation.add_pool_object(label, position, self.scores[label])

    def predict_image(self, screen):
        filename = config.TEMPORARY_IMAGE_NAME
        cv2.imwrite(filename, screen)
        image = utils.read_image(filename)
        return self.model.predict_top(image)

    def get_bounding_boxes(self, screen):
        labels, boxes, scores  = self.predict_image(screen)
        self.scores = dict()
        bounding_boxes = dict()
        for index, label in enumerate(labels):
            assert (label in config.ALL_MODEL_LABELS)
            self.scores[label] = float(scores[index])
            bounding_box_float = boxes[index]
            bounding_box = ((round(bounding_box_float[0].item()), round(bounding_box_float[1].item())), (round(bounding_box_float[2].item()), round(bounding_box_float[3].item())))
            bounding_boxes[label] = bounding_box

        return bounding_boxes

    def get_ball_counts(self):
        assert(self.observation is not None)
        stripes,solids = 0, 0
        for label in config.ALL_MODEL_LABELS:
            if "pocket" in label or "white_ball" in label or "black_ball" in label:
                continue
            if not self.observation.balls_in_play[label]: continue
            if "stripe" in label:
                stripes += 1
            elif "solid" in label:
                solids += 1

        return stripes,solids