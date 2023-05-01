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
from bot_logger import log, draw_debug_image

class PoolGameEnvironment(object):
    def __init__(self):
        self.state = State()
        self.pool_input = PoolInput()
        model = self.load_object_detection_model()
        self.pool_model = PoolModel(model)
        self.angle_mover = self.get_angle_mover()

    def draw_debug_image(self, angle):
        return
        # TODO fix
        # frame = self.get_frame()
        # bounding_boxes = dict()
        # ((sx, sy), (ex, ey)) = self.angle_mover.table_bounding_box
        # width,height = ex-sx, ey-sy
        # for label in self.pool_model.bounding_boxes:
        #     if not "pocket" in label:
        #         if self.pool_model.observation.balls_in_play[label] > 0.9: ## TODO get threshold from pool_model script
        #             x, y = self.pool_model.observation.positions[label]
        #             px, py = math.floor(sx + x*width), math.floor(sy + y*height)
        #             bounding_boxes[label] = px, py
        #     else:
        #         bounding_boxes[label] = self.pool_model.bounding_boxes[label]


        # draw_debug_image(frame, bounding_boxes, angle)

    def reset(self):
        ## TODO reset game to start 
        ## for now assuming game is in a reset position
        return self.get_observations()

    def step(self, action): ## TODO make action more than just angle
        ## TODO our object detection does seem to false flag so that needs to be improved for a more robust training
        angle = float(action * 2 * math.pi)
        shot = Shot(angle=angle, cue_mouse_delta=(0, 0), shot_back_distance=200, shot_forward_distance=400)
        self.get_to_overhead_position()
        previous_remaining_striped_balls, previous_remaining_solid_balls = self.pool_model.get_ball_counts()
        self.perform_shot(shot)
        previous_pool_type = self.state.current_pool_type
        win_state, scratched, scratched_before_win = self.get_to_overhead_position()
        new_pool_type = self.state.current_pool_type
        new_remaining_striped_balls, new_remaining_solid_balls = self.pool_model.get_ball_counts()
        ##TODO since we mostly return -8 this code will be a lot simpler if we only check the cases where we don't fail
        ## Reward function for now
        ## any loss -8
        ## any the number of balls of our colour go down or the same between turns -8 (heavily penalise bad turns as if they are losses)
        ## any win = 8 points
        ## 1 point for each ball of our colour potted

        if win_state == WinState.WON:
            if scratched_before_win:
                log("We won but because our opponent scratched")
                reward = -8
                done = True
            else:
                log("We won")
                reward = 8
                done = True
        elif win_state == WinState.LOST:
            log("We lost")
            reward = -8
            done = True
        else:
            if previous_pool_type == CurrentPoolType.ANY:
                if new_pool_type == CurrentPoolType.SOLID and new_remaining_striped_balls == 7:
                    log("We managed to pocket one type of ball when we can hit any ball")
                    reward = 8 - new_remaining_solid_balls
                if new_pool_type == CurrentPoolType.STRIPES and new_remaining_solid_balls == 7:
                    log("We managed to pocket one type of ball when we can hit any ball")
                    reward = 8 - new_remaining_striped_balls
                else:
                    log("No one manged to hit a ball when the pool type hasn't been determined")
                    reward = -8 ##  ## assume neither of us managed to get a ball in with only one colour
            elif previous_pool_type == CurrentPoolType.SOLID:
                if previous_remaining_striped_balls > new_remaining_striped_balls or previous_remaining_solid_balls == new_remaining_solid_balls:
                    log("We didn't pocket any solid balls")
                    reward = -8
                else:
                    if scratched:# if only our count went down but someone scratched is either us or our opponent had a turn -8 reward
                        log("We managed to pocket a solid ball but we scratched")
                        reward = -8
                    else:
                        reward = previous_remaining_solid_balls - new_remaining_solid_balls
                        log("We mananged to pocket {reward} solid balls".format(reward = reward))

            elif previous_pool_type == CurrentPoolType.STRIPES:
                if previous_remaining_solid_balls > previous_remaining_solid_balls or previous_remaining_striped_balls == new_remaining_striped_balls:
                    reward = -8
                    log("We didn't pocket any striped balls")
                else:
                    if scratched: # same reasoning as above
                        log("We managed to pocket a striped ball but we scratched")
                        reward = -8
                    else:
                        reward = previous_remaining_striped_balls - new_remaining_striped_balls
                        log("We mananged to pocket {reward} striped balls".format(reward = reward))
            else:
                log("Got pool type any not expecting that will just set reward to 0 ...")
                reward = 0 
            done = False

        new_state  = self.get_observations()
        return new_state, reward, done, None

    def perform_shot(self, shot):
        self.move_to_angle(shot.angle)
        self.draw_debug_image(shot.angle)
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

    # Also reports on who won since last time
    def get_to_overhead_position(self):
        returned_win_state = WinState.GAME_IN_PROGRESS
        scratched = False
        scratched_before_win = False
        while True:
            self.update_state()
            scratched = scratched or self.state.scratched
            if returned_win_state == WinState.GAME_IN_PROGRESS and self.state.win_state != WinState.GAME_IN_PROGRESS:
                returned_win_state = self.state.win_state
                scratched_before_win = scratched and self.state.win_state == WinState.WON
            if self.state.current_state == PoolState.OVERHEAD:
                return returned_win_state, scratched, scratched_before_win
            elif self.state.current_state == PoolState.NORMAL_VIEW:
                self.pool_input.press_v()
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
