from pool_state import State, PoolState, CurrentPoolType, Shot, WinState
from pool_input import PoolInput
from pool_model import PoolModel
from angle_mover import AngleMover
import grabscreen
import win32gui
import config
import cv2
from pytesseract import pytesseract
from detecto.core import Model
import math

import time # Remove after using proper reward function

class PoolGameEnvironment(object):
    def __init__(self):
        self.state = State()
        self.pool_input = PoolInput()
        model = self.load_object_detection_model()
        self.pool_model = PoolModel(model)
        self.angle_mover = self.get_angle_mover()

    def reset(self):
        ## TODO reset game to start 
        ## for now assuming game is in a reset position
        return self.get_observations()

    def step(self, action): ## TODO make action more than just angle
        angle = float(action * 2 * math.pi)
        shot = Shot(angle=angle, cue_mouse_delta=(0, 0), shot_back_distance=200, shot_forward_distance=400)
        self.get_to_overhead_position()
        before_time = time.time()
        self.perform_shot(shot)
        self.get_to_overhead_position()
        after_time = time.time() ## as a test the time taken between shots is shorter if we don't miss so is a good proxy for a reward func
        scratched = self.state.scratched
        win_state = self.state.win_state
        self.state.clear()

        # ## TODO for now we just have +1 for not scratching and -1 for scratching
        # ## add better reward function that takes into account number of turns taken to win and the number of balls left or avg distance from pockets...
        # if win_state == WinState.WON:
        #     reward = 1
        #     done = True
        # elif win_state == WinState.LOST or scratched:
        #     reward = -1
        #     done = True ## TODO for now treat scratching as a loss to test
        # else:
        #     reward = 0
        #     done = False

        ## testing out with simple reward function 1 if we didn't scratch otherwise -1
        done = True
        reward = -(after_time - before_time)

        new_state  = self.get_observations()
        return new_state, reward, done, None

    def perform_shot(self, shot):
        self.move_to_angle(shot.angle)
        self.pool_input.left_click()
        # TODO move cue to delta
        self.hit_cue_ball(shot)

    def move_to_angle(self, desired_angle):
        self.angle_mover.with_bounding_boxes(self.pool_model.bounding_boxes).move_to(desired_angle)

    def hit_cue_ball(self, shot):
        self.update_state()
        assert(self.state.current_state == PoolState.AIMING)
        while self.state.current_state == PoolState.AIMING: ## we do this because sometimes the shot isn't taken
            self.pool_input.wait(1)
            self.pool_input.take_shot(shot.shot_back_distance, shot.shot_forward_distance) 
            self.pool_input.wait(1)
            self.update_state()

    def get_to_overhead_position(self):
        while True:
            self.update_state()
            if self.state.current_state == PoolState.OVERHEAD:
                return
            elif self.state.current_state == PoolState.NORMAL_VIEW:
                self.pool_input.pres_v()
            elif self.state.current_state == PoolState.RESTART:
                self.pool_input.press_enter()
            elif self.state.current_state == PoolState.POSITIONING:
                self.pool_input.left_click() # TODO calculate a good position
            elif self.state.current_state == PoolState.MUST_SHOW_HELP:
                self.pool_input.press_backspace()

    def get_observations(self):
        self.get_to_overhead_position()
        assert(self.state.current_pool_type in [CurrentPoolType.SOLID, CurrentPoolType.STRIPES, CurrentPoolType.ANY] )
        ## TODO for now we assume we want to hit a solid ball if we have yet to be given a pool type
        self.pool_model.load_frame(self.get_frame(), is_solid = self.state.current_pool_type in [CurrentPoolType.SOLID, CurrentPoolType.ANY])
        return self.pool_model.observation.to_array()
        
    def update_state(self):
        frame = self.get_frame()
        text = self.get_text_from_frame(frame)
        self.state.update_from_text(text)       

    def get_frame(self):
        window_handle = win32gui.FindWindow(None, config.GAME_NAME)
        rect = win32gui.GetWindowRect(window_handle)
        return grabscreen.grab_screen(rect)
    
    def get_text_from_frame(self, frame):
        frame, gray_frame = self.preprocess_frame(frame)
        pytesseract.tesseract_cmd = config.PATH_TO_TESSERACT_EXE
        text1 = pytesseract.image_to_string(frame)
        text2 = pytesseract.image_to_string(gray_frame)
        return text1 + text2

    def preprocess_frame(self, frame):
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return frame, gray_frame # some text is better read with colour so we join lol

    def load_object_detection_model(self):
        return Model.load(config.TRAINING_MODEL_FILENAME, config.ALL_MODEL_LABELS)
    
    def get_angle_mover(self):
        def get_frame_function():
            return self.get_frame()
        
        def move_clockwise_function(duration_seconds):
            self.pool_input.move_angle_clockwise(duration_seconds) 

        def move_anticlockwise_function(duration_seconds):
            self.pool_input.move_angle_anticlockwise(duration_seconds)

        return AngleMover(move_clockwise_function, move_anticlockwise_function, get_frame_function)
