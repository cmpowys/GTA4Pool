import config
from pytesseract import pytesseract
import win32gui
import grabscreen
from detecto.core import Model
import cv2
from enum import Enum
import numpy as np
import time
import Levenshtein
from itertools import combinations
from pool_input import PoolInput
from trajectory import get_angle
import math

def get_text_from_frame(frame):
    # TODO preprocess image for better results? some text like "You lose" is missing from bottom and its in red
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    pytesseract.tesseract_cmd = config.PATH_TO_TESSERACT_EXE
    return pytesseract.image_to_string(gray_frame)

def get_frame():
    window_handle = win32gui.FindWindow(None, config.GAME_NAME)
    rect = win32gui.GetWindowRect(window_handle)
    return grabscreen.grab_screen(rect), rect


def load_object_detection_model():
    return Model.load(config.TRAINING_MODEL_FILENAME, config.ALL_MODEL_LABELS)

    #return pickle.load(open(config.OBJECT_DETECTION_MODEL, "rb"))


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

class Shot(object):
    def __init__(self, angle, cue_mouse_delta, shot_back_distance, shot_forward_distance):
        self.angle = angle
        self.cue_mouse_delta = cue_mouse_delta
        self.shot_back_distance = shot_back_distance
        self.shot_forward_distance = shot_forward_distance

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

def display_image(image):
    cv2.imshow(config.DISPLAY_WINDOW_NAME, image)

def create_named_window(x, y):
    width, height = config.DISPLAY_WINDOW_SHAPE
    cv2.namedWindow(config.DISPLAY_WINDOW_NAME)
    cv2.moveWindow(config.DISPLAY_WINDOW_NAME, x, y)
    cv2.resizeWindow(config.DISPLAY_WINDOW_NAME, width, height)

def create_random_shot():
    return Shot(0, (0, 0), 200, 400)

def perform_shot(pool_input, shot, model):
    move_to_angle(pool_input, shot.angle, model)
    #pool_input.left_click()
    # move cue to delta
    #pool_input.take_shot(shot.shot_back_distance, shot.shot_forward_distance)

def move_to_angle(pool_input, angle, model):
    def get_frame_function():
        frame, _ = get_frame()
        return frame
    
    while True:
        get_angle(model, get_frame_function)
    
    # TOLERANCE = 0.1
    # DURATION = 0.3
    # print("Starting angle move")
    # current_angle = get_angle(model, get_frame_function)
    # print("Got first angle", current_angle)
    # while abs(angle - current_angle) >= TOLERANCE:
    #     print("About to move")
    #     pool_input.move_angle(DURATION)
    #     new_angle = get_angle(model, get_frame_function)
    #     print("New angle=", new_angle, "Current angle=", current_angle, "Difference=", new_angle-current_angle)
    #     radians_per_second = (new_angle-current_angle) / DURATION
    #     print("Moved {radians_per_second} radians/ms".format(radians_per_second=radians_per_second))
    #     current_angle = new_angle



def move_to_overhead_view(pool_input):
    pool_input.press_v()

class BotContext:
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, tb):
        cv2.destroyAllWindows()

if __name__ == "__main__":
    with BotContext():
        pool_input = PoolInput()
        model = load_object_detection_model()
        frame, _ = get_frame()
        state = State()
        #create_named_window(-1000, 400)

        while True:
            frame, _ = get_frame()
            text = get_text_from_frame(frame)
            state.update_from_text(text)
            perform_shot(pool_input, create_random_shot(), model)

            # if state.current_state == PoolState.OVERHEAD:
            #     shot = create_random_shot()
            #     perform_shot(pool_input, shot, model)
            # elif state.current_state == PoolState.NORMAL_VIEW:
            #     move_to_overhead_view(pool_input)
            # elif state.current_state == PoolState.RESTART:
            #     pool_input.press_enter()
            # elif state.current_state == PoolState.POSITIONING:
            #     pool_input.left_click() # TODO calculate a good position
            # elif state.current_state == PoolState.MUST_SHOW_HELP:
            #     pool_input.press_backspace()
            
            # time.sleep(1)