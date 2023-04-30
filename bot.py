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
import math
import random
from bot_logger import log, draw_debug_image
from pool_model import PoolModel
from angle_mover import AngleMover

def get_text_from_frame(frame):
    # TODO preprocess image for better results? some text like "You lose" is missing from bottom and its in red
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    pytesseract.tesseract_cmd = config.PATH_TO_TESSERACT_EXE
    text = pytesseract.image_to_string(gray_frame)
    return text

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
        self.scratched = False

    def __str__(self):
        return "{state},{type}".format(state = self.current_state, type = self.current_pool_type)
    
    def clear_strached(self):
        self.scratched = False

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

        scratch_choice = {
            "scratch" : True
        }

        self.current_pool_type = text.get_state(pool_type_choices, self.current_pool_type, THRESHOLD)
        self.current_state = text.get_state(state_choices, PoolState.WAITING, THRESHOLD)
        self.scratched = self.scratched or text.get_state(scratch_choice, False, THRESHOLD)

def display_image(image):
    cv2.imshow(config.DISPLAY_WINDOW_NAME, image)

def create_named_window(x, y):
    width, height = config.DISPLAY_WINDOW_SHAPE
    cv2.namedWindow(config.DISPLAY_WINDOW_NAME)
    cv2.moveWindow(config.DISPLAY_WINDOW_NAME, x, y)
    cv2.resizeWindow(config.DISPLAY_WINDOW_NAME, width, height)

def create_random_shot():
    angle = random.random() * 2 * math.pi
    return Shot(angle, (0, 0), 200, 400)

def perform_shot(state, pool_input, angle_mover, shot, pool_model):
    log("About to move angle")
    move_to_angle(angle_mover, shot.angle, pool_model)
    log("About to go to aim mode")
    pool_input.left_click()
    # TODO move cue to delta
    hit_cue_ball(state, shot)

def move_to_angle(angle_mover, desired_angle, pool_model):
    angle_mover.with_bounding_boxes(pool_model.bounding_boxes).move_to(desired_angle)

def hit_cue_ball(state, shot):
    state.current_state = PoolState.AIMING
    first_shot = True
    log("About to take shot!")
    while state.current_state == PoolState.AIMING: ## we do this because sometimes the shot isn't taken
        if not first_shot:
            log("Missed shot for some reason, will try again")
        pool_input.wait(1)
        pool_input.take_shot(shot.shot_back_distance, shot.shot_forward_distance) 
        pool_input.wait(1)

        frame, _ = get_frame()
        text = get_text_from_frame(frame)
        state.update_from_text(text)
        first_shot = False

def move_to_overhead_view(pool_input):
    pool_input.press_v()

def create_shot_oriented_towards_black_ball(pool_model):
    angle_to_black_ball = pool_model.get_angle_to("black_ball")
    return Shot(angle_to_black_ball, (0, 0), 200, 400)

class BotContext:
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, tb):
        cv2.destroyAllWindows()

def get_angle_mover(pool_input):
    def get_frame_function():
        frame, _ = get_frame()
        return frame
    
    def move_clockwise_function(duration_seconds):
        pool_input.move_angle_clockwise(duration_seconds) 

    def move_anticlockwise_function(duration_seconds):
        pool_input.move_angle_anticlockwise(duration_seconds)

    return AngleMover(move_clockwise_function, move_anticlockwise_function, get_frame_function)

if __name__ == "__main__":
    with BotContext():
        frame, _ = get_frame()
        pool_input = PoolInput()
        model = load_object_detection_model()
        pool_model = PoolModel(model)
        angle_mover = get_angle_mover(pool_input)
        state = State()

        #create_named_window(-1000, 400)

        while True:
            frame, _ = get_frame()
            text = get_text_from_frame(frame)
            state.update_from_text(text)

            if state.current_state == PoolState.OVERHEAD:
                pool_model.load_frame(frame)
                shot = create_shot_oriented_towards_black_ball(pool_model)
                perform_shot(state, pool_input, angle_mover, shot, pool_model)
            elif state.current_state == PoolState.NORMAL_VIEW:
                move_to_overhead_view(pool_input)
            elif state.current_state == PoolState.RESTART:
                pool_input.press_enter()
            elif state.current_state == PoolState.POSITIONING:
                pool_input.left_click() # TODO calculate a good position
            elif state.current_state == PoolState.MUST_SHOW_HELP:
                pool_input.press_backspace()
            
            if state.scratched:
                log("Someone scratched!")
            time.sleep(1)