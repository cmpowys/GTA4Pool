import config
from pytesseract import pytesseract
import win32gui
import grabscreen
import pickle
import cv2
from enum import Enum
from collections import defaultdict
import numpy as np
import math

def get_text_from_frame(frame):
    # TODO preprocess image for better results?
    pytesseract.tesseract_cmd = config.PATH_TO_TESSERACT
    return pytesseract.image_to_string(frame)


def get_frame():
    window_handle = win32gui.FindWindow(None, config.GAME_NAME)
    rect = win32gui.GetWindowRect(window_handle)
    return grabscreen.grab_screen(rect), rect


def load_object_detection_model():
    return pickle.load(open(config.OBJECT_DETECTION_MODEL, "rb"))


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


def detect_pool_objects(frame, model):
    filename = config.TEMPORARY_IMAGE_NAME
    cv2.imwrite(filename, frame)

    predictions = model.predict(filename, confidence=40, overlap=30)
    return [Prediction(p) for p in predictions]


def group_preditions_by_class(predictions):
    grouping = defaultdict(lambda: [])
    for p in predictions:
        grouping[p.classification].append(p)


def display_predictions(predictions):
    image = np.ones(config.DISPLAY_WINDOW_SHAPE)
    for p in predictions:
        if p.classifiction == Classification.MARKER:
            cv2.circle(image, p.center, 3, (50, 50, 50))
        elif p.Classification == Classification.SOLID:
            cv2.circle(image, p.center, 5, (255, 0, 0))
        # TODO

    display_image(image)


def display_image(image):
    cv2.imshow(config.DISPLAY_WINDOW_NAME, image)


def create_named_window(x, y):
    width, height = config.DISPLAY_WINDOW_SHAPE
    cv2.namedWindow(config.DISPLAY_WINDOW_NAME)
    cv2.moveWindow(config.DISPLAY_WINDOW_NAME, x, y)
    cv2.resizeWindow(config.DISPLAY_WINDOW_NAME, width, height)


class BotContext:
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, tb):
        cv2.destroyAllWindows()


if __name__ == "__main__":
    with BotContext():
        model = load_object_detection_model()
        frame, _ = get_frame()
        create_named_window(0, 0)

        while True:
            frame, _ = get_frame()
            text = get_text_from_frame(frame)
            predictions = detect_pool_objects(frame, model)
            display_predictions(predictions)
            print("New Frame:")
            print(text)
            cv2.waitKey(1000)