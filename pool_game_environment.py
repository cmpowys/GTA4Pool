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
        colourings = {
            'red' : (255, 0, 0),
            'purple' : (90,0,90), ##800080
            'black' : (0, 0, 0),
            'white' : (255, 255, 255),
            'green' : (0, 255, 0),
            'blue' : (0, 0, 255),
            'brown' : (165,42,42),#A52A2A
            'yellow' : (255, 255, 0),
            'orange' : (255, 165, 0) ##FFA500
        }

        ## TODO change above data so I don't have to swap here
        def get_colour_from_label(label):
            for colour in colourings:
                if colour in label:
                    c = colourings[colour]
                    return c[2], c[1], c[0]
            assert(False)

        def get_line_with_angle(start, angle, length):
            sx, sy = start
            y = -round(length*math.sin(angle))
            x = round(length*math.cos(angle))
            return (sx, sy, sx + x, sy + y)

        ((start_x, start_y), (end_x, end_y)) = self.angle_mover.table_bounding_box
        frame = self.get_frame()
        width, height = end_x - start_x, end_y - start_y
        # Draw table border
        cv2.rectangle(frame, (start_x, start_y), (end_x, end_y), (255, 255, 255), 1)
        for label in config.ALL_MODEL_LABELS:
            if not self.pool_model.observation.balls_in_play[label]: continue
            fpos_x, fpos_y = self.pool_model.observation.positions[label] 
            pos_x, pos_y = math.floor(start_x + (width*fpos_x)), math.floor(start_y + (height*fpos_y))
            ((tlx, tly), (brx, bry)) = self.pool_model.bounding_boxes[label]
            rx = (brx-tlx)/2
            ry = (bry-tly)/2
            radius = math.floor((rx + ry) / 2)

            if "pocket" in label:
                cv2.circle(frame, (pos_x, pos_y), radius, (100, 100, 100), 3)
            else:
                if "stripe" in label:
                    thickness = 1
                else:
                    thickness = 3
                colour = get_colour_from_label(label)
                cv2.circle(frame, (pos_x, pos_y), radius, colour, thickness)

        (mx, my) = self.angle_mover.middle_of(self.pool_model.bounding_boxes["white_ball"])
        (sx, sy, ex, ey) = get_line_with_angle((mx, my), angle, 500)
        cv2.line(frame, (sx, sy), (ex, ey), (50, 50, 50), 5)
        cv2.imshow(config.DISPLAY_WINDOW_NAME, frame)
        cv2.waitKey(1)

    def reset(self):
        self.get_to_overhead_position()
        return self.get_observations()

    def step(self, action): ## TODO make action more than just angle
        ## TODO our object detection does seem to false flag so that needs to be improved for a more robust training
        angle = float(action * 2 * math.pi)
        shot = Shot(angle=angle, cue_mouse_delta=(0, 0), shot_back_distance=200, shot_forward_distance=400)
        self.get_to_overhead_position()
        self.get_observations()
        previous_remaining_striped_balls, previous_remaining_solid_balls = self.pool_model.get_ball_counts()
        self.perform_shot(shot)
        previous_pool_type = self.state.current_pool_type
        win_state, scratched, scratched_before_win = self.get_to_overhead_position()
        self.get_observations()
        new_pool_type = self.state.current_pool_type
        new_remaining_striped_balls, new_remaining_solid_balls = self.pool_model.get_ball_counts()
        log("Previous striped balls was {ps}, Previous solid balls was {psd}".format(ps=previous_remaining_striped_balls, psd=previous_remaining_solid_balls))
        log("Remaining striped balls is {ps}, Remaining solid balls is {psd}".format(ps=new_remaining_striped_balls, psd=new_remaining_solid_balls))
        reward = 1
        if win_state == WinState.WON:
            if not scratched_before_win:
                log("We managed to win")
                reward = 10
            else:
                reward = -1
                log("We managed to win only because the other player scratched")
        elif win_state == WinState.LOST:
            log("We lost")
            reward = -10
        elif scratched: ## someone must have scratched either we didn't get a ball in (other player scratched) or we scratched
            log("Someone scratched either us or our opponent which would mean we gave him the opportunity to play")
            reward = -1
        else:
            if previous_pool_type == CurrentPoolType.ANY and new_pool_type != CurrentPoolType.ANY:
                if new_pool_type == CurrentPoolType.SOLID and new_remaining_striped_balls > new_remaining_solid_balls:
                    log("We have been moved to the solid ball but there are more stripes we must have lost")
                    reward = -1
                if new_pool_type == CurrentPoolType.STRIPES and new_remaining_solid_balls > new_remaining_striped_balls:
                    log("We have been moved to the striped ball but there are more solids we must have lost")
                    reward = -1
            elif new_pool_type == CurrentPoolType.SOLID and new_remaining_striped_balls < previous_remaining_striped_balls:
                log("We are solid but there are fewer striped balls, must have lost")
                reward = -1
            elif new_pool_type == CurrentPoolType.SOLID and new_remaining_solid_balls >= previous_remaining_solid_balls:
                reward = -1
                log("We are solid but the number didn't go down we must have missed")
            elif new_pool_type == CurrentPoolType.STRIPES and new_remaining_solid_balls < previous_remaining_solid_balls:
                log("We are striped but there are fewer solid balls, must have lost")
                reward = -1
            elif new_pool_type == CurrentPoolType.STRIPES and new_remaining_striped_balls >= previous_remaining_striped_balls:
                reward = -1
                log("We are striped but the number didn't go down we must have missed")

        if reward == 1:
            log("We managed to get a ball in")
                
        new_state  = self.get_observations()
        done = True # learning turn by turn for now
        info = None # not used
        return new_state, reward, done, info
        ## TODO do more sophisticated reward funtion later
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
        #self.draw_debug_image(shot.angle)
        self.pool_input.left_click()
        # TODO move cue to delta
        self.hit_cue_ball(shot)

    def move_to_angle(self, desired_angle):
        self.angle_mover.with_bounding_boxes(self.pool_model.bounding_boxes).move_to(desired_angle)

    def hit_cue_ball(self, shot): ## TODO just fail if we miss the first time
        self.update_state()
        assert(self.state.current_state == PoolState.AIMING)
        self.pool_input.wait(1)
        self.pool_input.take_shot(shot.shot_back_distance, shot.shot_forward_distance) 
        self.pool_input.wait(1)
        self.update_state()
        if self.state.current_state in [PoolState.AIMING]:
            self.pool_input.press_backspace()

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
        assert(self.state.current_pool_type in [CurrentPoolType.SOLID, CurrentPoolType.STRIPES, CurrentPoolType.ANY] )
        self.pool_model.load_frame(self.get_frame(), self.state.current_pool_type)
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
