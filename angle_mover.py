import numpy as np
import cv2
import math
from enum import Enum
from bot_logger import log

ESTIMATED_RADIANS_PER_SECOND = 0.2 # radians per second to move cue angle with spacebar held
NUM_ITERATIONS_TO_STABILISE_GAME_IMAGE = 100 ## more sophistacted means of breaking the loop here
BALL_RADIUS_SHRINK_FACTOR = 0.75 # This is to get the radius of the ball to match more closely. This is not so important for bot performance
DURATION_TO_MOVE_INITIALLY = 2 # number of seconds we move the cue angle initially when determining what the initial angle guess would be
ESTIMATED_RADIANS_PER_SECOND = 0.2 # Initial guess of how many radians per second we move
INITIAL_TRAJECTORY_TEST_SIZE = 150 ## instead of testing the trajectory with the full image for performance reasons
SECOND_TRAJECTORY_TEST_SIZE = 1000000 ## min/max should just result in the full image being returned simpler to code than having a special case in the algorithm
NUM_SECTORS_TO_INITIALLY_TEST = 4 # Number of sectors to initially test when determining angle
ANGLE_DELTA = 0.01 # resolution of angle test
MAX_MOVEMENTS_TOWARDS_ANGLE = 10 # when honing down on target angle we make at most this amount of movements
SCORE_THRESHOLD = 0.7
MAX_INITIAL_TRAJECTORY_TEST_SIZE = 8*INITIAL_TRAJECTORY_TEST_SIZE ## If we fail to threshold we keep increasing size by a factor of 2 until this size
THRESHOLD_FAIL_MOVE_DURATION = 3 # if we fail to threshold the sector guesses then move the cue to hopefully get a better angle calculation

class Direction(Enum):
    CLOCKWISE = 0
    ANTI_CLOCKWISE = 1

    def __str__(self):
        if self == Direction.CLOCKWISE:
            return "clockwise"
        else:
            return "anticlockwise"

class AngleMover(object):
    def __init__(self, move_clockwise_function, move_anti_clockwise_function, get_frame_function):
        self.estimated_radians_per_second = ESTIMATED_RADIANS_PER_SECOND
        self.move_clocwise_function = move_clockwise_function
        self.move_anti_clockwise_function = move_anti_clockwise_function
        self.get_frame_function = get_frame_function

    def adjust_radians_per_second_estimate(self, radians_per_second):
        new_estimated_radians_per_second = (self.estimated_radians_per_second + radians_per_second) / 2
        #log("Improved radians per second estimate from {old} to {new} with calculated radians per second {rps}."
            #.format(old=self.estimated_radians_per_second, new=new_estimated_radians_per_second, rps=radians_per_second))
        self.estimated_radians_per_second = new_estimated_radians_per_second
        
    def move_to(self, angle):
        log("Attemping move to {angle} radians".format(angle=angle))
        current_angle = self.make_initial_angle_estimate()
        #log("Angle estimated to be {current_angle}".format(current_angle=current_angle))

        for _ in range(MAX_MOVEMENTS_TOWARDS_ANGLE):
            #log("About to make move attempt")
            estimated_radians_moved, direction = self.make_move_attempt(current_angle, angle)
            game_trajectory_image = self.get_game_trajectory_image()
            estimated_angle, _ = self.make_angle_guess_within_range(current_angle, estimated_radians_moved, game_trajectory_image, direction)
            #log("After movement we have an estimated angle of {estimated_angle} radians".format(estimated_angle=estimated_angle))
            delta = abs(estimated_angle - angle)
            #log("Delta between desired and target angle is {delta}".format(delta=delta))
            ## TODO improve radians per second estimate
            if delta < 2*ANGLE_DELTA: ## TODO better angle tolerance
                log("We have reached our target angle")
                return
            #log("Angle not within tolerance")
            current_angle = estimated_angle
        #log("We have been unable to reach target angle within {steps} steps".format(steps = MAX_MOVEMENTS_TOWARDS_ANGLE))

    def make_move_attempt(self, current_angle, target_angle):
        clockwise_difference = self.get_radian_difference(current_angle, target_angle, Direction.CLOCKWISE)
        anticlockwise_difference = self.get_radian_difference(current_angle, target_angle, Direction.ANTI_CLOCKWISE)

        if clockwise_difference < anticlockwise_difference:
            direction = Direction.CLOCKWISE
            abs_radians = clockwise_difference
        else:
            direction = Direction.ANTI_CLOCKWISE
            abs_radians = anticlockwise_difference

        duration = abs_radians / self.estimated_radians_per_second
        #log("Calculated that we are {abs_radians} radians away with a(n) {direction} movement which will take {duration} seconds."
            #.format(abs_radians=abs_radians, direction=direction, duration=duration))
        
        if direction == Direction.CLOCKWISE:
            self.move_clocwise_function(duration)
        else:
            self.move_anti_clockwise_function(duration)

        return abs_radians, direction

    def with_bounding_boxes(self, bounding_boxes):
        self.bounding_boxes = bounding_boxes
        self.calculate_table_border_lines()
        self.calculate_table_bounding_box()
        return self

    def make_angle_guess_in_sectors(self, size):
        #log("Making initial angle estimate finding best within a number of sectors")
        game_trajectory_image = self.get_game_trajectory_image()
        guesses = []
        sector_length = 2*math.pi/NUM_SECTORS_TO_INITIALLY_TEST
        for sector_num in range(NUM_SECTORS_TO_INITIALLY_TEST):
            start = sector_num*sector_length
            if sector_num == NUM_SECTORS_TO_INITIALLY_TEST - 1:
                end = 2*math.pi
            else:
                end = (sector_num + 1)*sector_length
            #log("About to test in sector with start={start}, end={end}".format(start=start, end=end))
            angles_to_test = self.get_angles_to_test(start, end, ANGLE_DELTA)
            sector_guess = self.estimate_with(angles_to_test, game_trajectory_image, size)
            guesses.append(sector_guess)

        assert(len(guesses) > 0)
        guesses.sort(reverse=True, key=lambda x: x[1])
        
        #log("After testing in each sector we find the best guess in each sector (ordered by score) is {guesses}"
            #.format(guesses=str(guesses)))

        return guesses

    def make_angle_guess_within_range(self, start_angle, estimated_radians_moved, game_trajectory_image, direction):
        angles_to_test = self.get_angle_range_after_movement(start_angle, estimated_radians_moved, direction)
        estimated_angle, new_score = self.estimate_with(angles_to_test, game_trajectory_image, SECOND_TRAJECTORY_TEST_SIZE)
        return estimated_angle, new_score

    def make_initial_angle_estimate(self, size = INITIAL_TRAJECTORY_TEST_SIZE):
        best_guesses_per_sector = self.make_angle_guess_in_sectors(size)

        thresholded_guesses = [(guess_angle, guess_score) for guess_angle, guess_score in best_guesses_per_sector if guess_score >= SCORE_THRESHOLD]
        #log("Thresholding initial sector guesses")
        if len(thresholded_guesses) == 0:
            #log("No guesses made it past the threshold will increase image size by a factor of 2")
            if (2*size > MAX_INITIAL_TRAJECTORY_TEST_SIZE):
                #log("But we have already increased size too much will just randonly move the cue instead")
                self.move_anti_clockwise_function(THRESHOLD_FAIL_MOVE_DURATION)
                return self.make_initial_angle_estimate()
            else:
                return self.make_initial_angle_estimate(2*size)
        elif len(thresholded_guesses) == 1:
            #log("Only one guess made it past the threshold will be using that as our first estimate")
            return thresholded_guesses[0][0]
        else:
            #log("Multiple guesses made it past the threshold")
            best_guesses_per_sector = thresholded_guesses

        #TODO average estimated radians moved as got keeps playing
        estimated_radians_moved = self.move_anticlockwise_a_bit()
        game_trajectory_image = self.get_game_trajectory_image()

        new_guesses = []
        for (angle, score) in best_guesses_per_sector:
            estimated_angle, new_score = self.make_angle_guess_within_range(angle, estimated_radians_moved, game_trajectory_image, Direction.ANTI_CLOCKWISE)
            new_guesses.append((estimated_angle, new_score, angle))

        new_guesses.sort(reverse=True, key=lambda x:x[1])
        assert(len(new_guesses) > 0)

        current_angle, old_angle =  new_guesses[0][0], new_guesses[0][2]
        radians_per_second = self.get_actual_radians_per_second(current_angle, old_angle, DURATION_TO_MOVE_INITIALLY)
        self.adjust_radians_per_second_estimate(radians_per_second)
        return current_angle

    def middle_of(self, bounding_box):
        ((tlx, tly), (brx, bry)) = bounding_box
        return tlx + ((brx - tlx) // 2), tly + ((bry - tly) // 2)

    def radius_of(self, bounding_box, center = None):
        if center is None:
            center = self.middle_of(bounding_box)

        ((tlx, tly), (brx, bry)) = bounding_box
        (cx, cy) = center
        return math.floor(BALL_RADIUS_SHRINK_FACTOR*(((cx - tlx)**2 + (cy - tly)**2)**0.5))

    def adjust_start(self, center):
        ((tlx, tly), (brx, bry)) = self.table_bounding_box
        cx, cy = center
        return cx - tlx, cy - tly
    
    def calculate_table_border_lines(self):
        def fudge_center(center, radius, dx, dy):
            FUDGE_FACTOR = 0.5 # it seems that the actual table border is half the radius towards the center of the table
            distance = radius*FUDGE_FACTOR
            cx, cy = center
            return math.floor(cx + (dx*distance)), math.floor(cy + (dy * distance))

        tl_pocket_center = self.middle_of(self.bounding_boxes["topleft_pocket"])
        tr_pocket_center = self.middle_of(self.bounding_boxes["topright_pocket"])
        bl_pocket_center = self.middle_of(self.bounding_boxes["bottomleft_pocket"])
        br_pocket_center = self.middle_of(self.bounding_boxes["bottomright_pocket"])

        tl_pocket_center = fudge_center(tl_pocket_center, self.radius_of(self.bounding_boxes["topleft_pocket"], tl_pocket_center), 1, 1)
        tr_pocket_center = fudge_center(tr_pocket_center, self.radius_of(self.bounding_boxes["topright_pocket"], tr_pocket_center), -1, 1)
        bl_pocket_center = fudge_center(bl_pocket_center, self.radius_of(self.bounding_boxes["bottomleft_pocket"], bl_pocket_center), 1, -1)
        br_pocket_center = fudge_center(br_pocket_center, self.radius_of(self.bounding_boxes["bottomright_pocket"], br_pocket_center), -1, -1)

        ## repeating some coords to ensure that lines are completely vertical/horizontal and there are no gaps in the corners
        self.border_lines = [
            (tl_pocket_center[0], tl_pocket_center[1], tr_pocket_center[0], tl_pocket_center[1]), ## upper line
            (tr_pocket_center[0], tl_pocket_center[1], tr_pocket_center[0], br_pocket_center[1]), ## right line
            (tr_pocket_center[0], br_pocket_center[1], bl_pocket_center[0], br_pocket_center[1]), ## bottom line
            (bl_pocket_center[0], br_pocket_center[1], bl_pocket_center[0], tl_pocket_center[1])  ## left line
        ]
    
    def calculate_table_bounding_box(self):
        self.table_bounding_box = ((self.border_lines[0][0], self.border_lines[0][1]), (self.border_lines[1][2], self.border_lines[1][3]))
    
    def crop_image_to_table(self, frame):
            ((tlx, tly), (brx, bry)) = self.table_bounding_box
            return frame[tly:bry, tlx:brx]
    
    def get_cropped_image(self):
        frame = self.get_frame_function()
        frame = self.crop_image_to_table(frame)
        return frame
    
    def get_adjusted_white_ball_center(self):
        ((tlx, tly), (brx, bry)) = self.table_bounding_box
        cx, cy = self.middle_of(self.bounding_boxes["white_ball"])
        return cx - tlx, cy - tly
    
    def get_simulated_trajectory(self, desired_angle):                
        def draw_line(image, line):
            cv2.line(image, (line[0], line[1]), (line[2], line[3]), (255, 255, 255), 4)

        def draw_trajectory(start, angle, length, image):
            def get_line_length(line):
                (sx, sy, ex, ey) = line
                return ((sx - ex)**2 + (sy - ey)**2)**0.5

            def get_line_with_angle(start, angle, length):
                sx, sy = start
                y = -round(length*math.sin(angle))
                x = round(length*math.cos(angle))
                return (sx, sy, sx + x, sy + y)

            def line_segments_intersect_with_point(line1, line2, point):
                ((x1, y1), (x2, y2)) = line1
                ((x3, y3), (x4, y4)) = line2
                x, y = point

                return (min(x1, x2) <= x <= max(x1, x2) and
                            min(y1, y2) <= y <= max(y1, y2) and
                            min(x3, x4) <= x <= max(x3, x4) and
                            min(y3, y4) <= y <= max(y3, y4))


            def line_intersection(line1, line2):
                line1 = ((line1[0], line1[1]), (line1[2], line1[3]))
                line2 = ((line2[0], line2[1]), (line2[2], line2[3]))
                xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
                ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

                def det(a, b):
                    return a[0] * b[1] - a[1] * b[0]

                div = det(xdiff, ydiff)
                if div == 0:
                    return None

                d = (det(*line1), det(*line2))
                x = det(d, xdiff) / div
                y = det(d, ydiff) / div
                if line_segments_intersect_with_point(line1, line2, (x,y)):
                    return math.floor(x), math.floor(y)

            if length <= 0:
                return
            
            width,height = image.shape[1], image.shape[0]
            border_lines = [
                (0, 0, width, 0),
                (width, 0, width, height),
                (width, height, 0, height),
                (0, height, 0, 0)
            ]

            line = get_line_with_angle(start, angle, length)

            least_line, least_length, intersected_border_index = None, 100000, -1
            for borderline_index, border_line in enumerate(border_lines):
                intersection = line_intersection(border_line, line)
                if not intersection is None:
                    line_to_draw = (line[0], line[1], intersection[0], intersection[1])
                    line_length = get_line_length(line_to_draw)
                    if line_length > 0 and line_length < least_length:
                        least_line, least_length, intersected_border_index = line_to_draw, line_length, borderline_index

            if not least_line is None:
                draw_line(image, least_line)
                remaining_length = length - least_length
                if intersected_border_index == 0:
                    reflected_angle = (2*math.pi) - angle
                if intersected_border_index == 1:
                    reflected_angle = (math.pi) - angle
                if intersected_border_index == 2:
                    reflected_angle = (2*math.pi) - angle
                if intersected_border_index == 3:
                    reflected_angle = (math.pi) - angle
                draw_trajectory((least_line[2], least_line[3]), reflected_angle, remaining_length, image)
            else: ## assume line ends in pool table
                draw_line(image, line)
        
        image = self.get_cropped_image()
        image = np.zeros_like(image)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        start = self.get_adjusted_white_ball_center()
        length = math.floor(image.shape[1]*1.5) # Trajectory length seems to be around 1.5 times the length of the table

        draw_trajectory(start, desired_angle, length, image)

        return image
    
    def get_game_trajectory_image(self):    
        def get_delta_image(previous_cropped_image, current_cropped_image):
            subtracted_area = previous_cropped_image - current_cropped_image
            subtracted_area = cv2.cvtColor(subtracted_area, cv2.COLOR_BGR2GRAY)
            subtracted_area = cv2.threshold(subtracted_area, 0, 255, cv2.THRESH_BINARY)[1]
            return subtracted_area
        
        previous_frame = self.get_cropped_image()
        trajectory_image = None
        for _ in range(NUM_ITERATIONS_TO_STABILISE_GAME_IMAGE):
            current_frame = self.get_cropped_image()
            delta_image = get_delta_image(previous_frame, current_frame)

            if trajectory_image is None:
                trajectory_image = delta_image
            else:
                new_image = trajectory_image | delta_image
                ## TODO more sophisticated test here to see if the delta image has stabilised
                trajectory_image = new_image

        return trajectory_image
    
    def get_bounded_image(self, image, size):
            (cx, cy) =  self.get_adjusted_white_ball_center()
            height, width = image.shape
            start_x = max(0, cx - size)
            start_y = max(0, cy - size)
            end_x = min(cx + size, width - 1)
            end_y = min(cx + size, height - 1)
            return image[start_y:end_y, start_x:end_x]

    def estimate_with(self, angles, full_game_image, size):
        small_game_image = self.get_bounded_image(full_game_image, size)
        best_angle, best_score = angles[0], 0
        for current_angle in angles:
            simulated_trajectory_image = self.get_simulated_trajectory(current_angle)
            small_simulated_trajectory_image = self.get_bounded_image(simulated_trajectory_image, size)
            score = self.evaluate_trajectory(small_simulated_trajectory_image, small_game_image)
            if score >= best_score:
                best_angle, best_score = current_angle, score

        return best_angle, best_score
    
    ## evaluates simulated trajectory with actual trajectory by counting how often we intersect divided by total number white pixels in simulated trajectory
    def evaluate_trajectory(self, simulated_trajectory_image, game_trajectory_image):
        intersected_image = simulated_trajectory_image & game_trajectory_image
        simulated_trajectory_sum = np.sum(simulated_trajectory_image == 255)
        intersected_sum = np.sum(intersected_image == 255)
        if simulated_trajectory_sum == 0:
            return 0
        assert(simulated_trajectory_sum > 0)
        score = intersected_sum / simulated_trajectory_sum
        assert(score >= 0 and score <= 1)
        return score
    
    def get_angles_to_test(self, start, end, difference):
        angles = []
        current_angle = start
        while current_angle < end:
            angles.append(current_angle)
            current_angle += difference
        return angles
        
    def move_anticlockwise_a_bit(self):
        self.move_anti_clockwise_function(DURATION_TO_MOVE_INITIALLY)
        return DURATION_TO_MOVE_INITIALLY * self.estimated_radians_per_second
    
    def get_angle_range_after_movement(self, old_angle, estimated_radians_moved, direction):
        if direction == Direction.ANTI_CLOCKWISE:
            estimated_angle = old_angle + estimated_radians_moved

            if estimated_angle > 2*math.pi:
                estimated_angle -= (2*math.pi)
        else:
            estimated_angle = old_angle - estimated_radians_moved

            if estimated_angle < 0:
                estimated_angle += (2*math.pi)

        bound = 0.5*estimated_radians_moved
        difference = ANGLE_DELTA
        angles_to_return = []
        angles_to_return.append(estimated_angle)
        lower_angle = estimated_angle
        upper_angle = estimated_angle
        for _ in range(1, math.floor(bound/difference)):
            lower_angle -= difference
            if lower_angle < 0:
                lower_angle = (2*math.pi) - lower_angle
            
            upper_angle += difference
            if upper_angle >= 2*math.pi:
                upper_angle -= 2*math.pi
            
            angles_to_return.append(lower_angle)
            angles_to_return.append(upper_angle)
        
        return angles_to_return
    
    def get_radian_difference(self, current_angle, target_angle, direction):
        if direction == Direction.ANTI_CLOCKWISE:
            angle, desired = current_angle, target_angle
        else:
            angle, desired = target_angle, current_angle

        if angle < desired:
            return desired - angle
        else:
            return desired + ((2*math.pi) - angle)

    def get_actual_radians_per_second(self, current_angle, old_angle, duration):
        absolute_difference = self.get_radian_difference(old_angle, current_angle, Direction.ANTI_CLOCKWISE)
        return absolute_difference / duration
