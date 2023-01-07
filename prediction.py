from enum import Enum
import math

class Classification(Enum):
    SOLID = 0,
    STRIPED = 1
    POCKET = 2
    MARKER = 3


class Prediction:
    def __init__(self, model_prediction):
        str_clasification = model_prediction["class"]
        if str_clasification == "pocket":
            self.classification = Classification.POCKET
        elif str_clasification == "solid":
            self.classification = Classification.SOLID
        elif str_clasification == "striped":
            self.classification = Classification.STRIPED
        elif str_clasification == "trajectory":
            self.classification = Classification.MARKER
        else:
            raise Exception("Unexpected classifiction " + str_clasification)

        x = model_prediction["x"]
        y = model_prediction["y"]
        width = model_prediction["width"]
        height = model_prediction["height"]

        topx = math.floor(x + (width/2))
        topy = math.floor(y + (height/2))
        botx = math.floor(topx - width)
        boty = math.floor(topy - height)

        side_lengthx = abs(topx - botx)
        side_lengthy = abs(topy - boty)
        average_side_length = math.floor((side_lengthx + side_lengthy) / 2)
        centerx = math.floor((topx + botx) / 2)
        centery = math.floor((topy + boty) / 2)

        self.center = (centerx, centery)
        self.radius = math.floor(average_side_length / 2)
        self.bounding_box = (topx, topy, botx, boty)
        self.number = 0 # TODO
        self.is_white = self.number == 16
