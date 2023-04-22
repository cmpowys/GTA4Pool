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
import time
import Levenshtein
from itertools import combinations

def get_text_from_frame(frame):
    # TODO preprocess image for better results?
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    pytesseract.tesseract_cmd = config.PATH_TO_TESSERACT_EXE
    return pytesseract.image_to_string(gray_frame)


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

class CurrentPoolType(Enum):
    UNKNOWN = 0
    SOLID = 1
    STRIPES = 2
    ANY = 3

class PoolState(Enum):
    UNKNOWN = 0
    WAITING = 1
    OVERHEAD = 2
    AIMING = 3
    PENDING_RESTART = 4
    POSITIONING = 5
    NORMAL_VIEW = 6,
    MUST_SHOW_HELP = 7
    RESTART = 8

def get_substrings(string):
    return [string[x:y] for x, y in combinations(range(len(string) + 1), r = 2)]

class FrameText(object):
    def __init__(self, text):
        self.text = text.lower()
        ## loop through all substrings of text
        ## find the top distance/ratio of all choices
        ## given a mininum ratio/distance so we don't choose bogus
        ## will output "default" state if nothing exceeds our threshold
        ## some text is lost need to preprocess frame further ("You Lost" in red at bottom of screen was missing)

    def get_state(self, choices, default, threshold_ratio):

        ratios = {}

        # get the max levenshtein distance ratio for each choice testing all substrings of the frame text
        for choice in choices:
            max_ratio, from_text = 0, ""
            for substring in get_substrings(self.text):
                ratio = Levenshtein.ratio(choice, substring)
                if ratio > max_ratio: max_ratio, from_text = ratio, substring
            ratios[choice] = (max_ratio, from_text)

        # find the choice that gives the highest ratio value that exceeds the past in ratio. If none exceed this ratio we will return the default
        max_ratio, state = 0, default
        for choice in ratios:
            (ratio, _) = ratios[choice]
            if (ratio > threshold_ratio) and ratio > max_ratio:
                max_ratio, state = ratio, choices[choice]

        return state

    def contains(self, other, choices):
        if other in self.text:
            return True
        
        options = [] ## need to iterate over all options then choose the highest with a min ratio for similar lines
        ## and over all possible subsets of the main text
        MIN_RATIO = 0.90
        for start_index in range(len(self.text)):
            end = min(start_index + len(other), len(self.text))
            substring = self.text[start_index : end]
            ratio = Levenshtein.ratio(substring, other)
            if ratio > MIN_RATIO:
                return True
        
        return False

class State(object):
    def __init__(self):
        self.current_pool_type = CurrentPoolType.UNKNOWN
        self.current_state = PoolState.UNKNOWN

    def __str__(self):
        return "{state},{type}".format(state = self.current_state, type = self.current_pool_type)

    def update_from_text(self, text):
        text = FrameText(text)

        THRESHOLD = 0.75

        pool_type_choices = {
            "you may hit any colored ball" : CurrentPoolType.ANY,
            "must hit a striped colored ball" : CurrentPoolType.STRIPES,
            "must hit a solid colored ball" : CurrentPoolType.SOLID
        }

        state_choices = {
            "to position cue ball" : PoolState.POSITIONING,
            "for normal view" : PoolState.OVERHEAD,
            "for overhead view" : PoolState.NORMAL_VIEW,
            "in one motion" : PoolState.AIMING,
            "to show help" :  PoolState.MUST_SHOW_HELP,
            "to play again" : PoolState.RESTART
        }

        self.current_pool_type = text.get_state(pool_type_choices, self.current_pool_type, THRESHOLD)
        self.current_state = text.get_state(state_choices, PoolState.WAITING, THRESHOLD)

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
        if p.classification == Classification.MARKER:
            cv2.circle(image, p.center, 3, (50, 50, 50))
        elif p.classification == Classification.SOLID:
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
        state = State()
        #create_named_window(0, 0)

        while True:
            frame, _ = get_frame()
            text = get_text_from_frame(frame)
            #print(text)
            state.update_from_text(text)
            print(state)
            time.sleep(1)
            #predictions = detect_pool_objects(frame, model)
            #display_predictions(predictions)
            #print("New Frame:")
            #cv2.waitKey(1000)