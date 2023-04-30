import math
import cv2
import config
import numpy as np
from bot_logger import log
from trajectory_mover import TrajectoryMover
from enum import Enum

class Direction(Enum):
    CLOCKWISE = 0
    ANTI_CLOCKWISE = 1

    def __str__(self):
        if self == Direction.CLOCKWISE:
            return "clockwise"
        else:
            return "anticlockwise"

def move_to_angle(angle, clockwise_movement_function, anti_clockwise_movement_function, frame_function, bounding_boxes):
    def middle_of(bounding_box):
        ((tlx, tly), (brx, bry)) = bounding_box
        return tlx + ((brx - tlx) // 2), tly + ((bry - tly) // 2)

    def radius_of(bounding_box, center):
        SHRINK_FACTOR = 0.75 # This is to get the radius of the ball to match more closely. This is not so important for bot performance
        ((tlx, tly), (brx, bry)) = bounding_box
        (cx, cy) = center
        return math.floor(SHRINK_FACTOR*(((cx - tlx)**2 + (cy - tly)**2)**0.5))
    
    def adjust_start(center):
        ((tlx, tly), (brx, bry)) = get_table_bounding_box(calculate_table_border_lines())
        cx, cy = center
        return cx - tlx, cy - tly
    
    def calculate_table_border_lines():
        def fudge_center(center, radius, dx, dy):
            FUDGE_FACTOR = 0.5 # it seems that the actual table border is half the radius towards the center of the table
            distance = radius*FUDGE_FACTOR
            cx, cy = center
            return math.floor(cx + (dx*distance)), math.floor(cy + (dy * distance))

        tl_pocket_center = middle_of(bounding_boxes["topleft_pocket"])
        tr_pocket_center = middle_of(bounding_boxes["topright_pocket"])
        bl_pocket_center = middle_of(bounding_boxes["bottomleft_pocket"])
        br_pocket_center = middle_of(bounding_boxes["bottomright_pocket"])

        tl_pocket_center = fudge_center(tl_pocket_center, radius_of(bounding_boxes["topleft_pocket"], tl_pocket_center), 1, 1)
        tr_pocket_center = fudge_center(tr_pocket_center, radius_of(bounding_boxes["topright_pocket"], tr_pocket_center), -1, 1)
        bl_pocket_center = fudge_center(bl_pocket_center, radius_of(bounding_boxes["bottomleft_pocket"], bl_pocket_center), 1, -1)
        br_pocket_center = fudge_center(br_pocket_center, radius_of(bounding_boxes["bottomright_pocket"], br_pocket_center), -1, -1)

        ## repeating some coords to ensure that lines are completely vertical/horizontal and there are no gaps in the corners
        return [
            (tl_pocket_center[0], tl_pocket_center[1], tr_pocket_center[0], tl_pocket_center[1]), ## upper line
            (tr_pocket_center[0], tl_pocket_center[1], tr_pocket_center[0], br_pocket_center[1]), ## right line
            (tr_pocket_center[0], br_pocket_center[1], bl_pocket_center[0], br_pocket_center[1]), ## bottom line
            (bl_pocket_center[0], br_pocket_center[1], bl_pocket_center[0], tl_pocket_center[1])  ## left line
        ]
    
    def get_table_bounding_box(border_lines):
        return ((border_lines[0][0], border_lines[0][1]), (border_lines[1][2], border_lines[1][3]))
    
    def crop_image_to_table(frame, border_lines):
            ((tlx, tly), (brx, bry)) = get_table_bounding_box(border_lines)
            return frame[tly:bry, tlx:brx]
    
    def get_cropped_image():
        frame = frame_function()
        frame = crop_image_to_table(frame, calculate_table_border_lines())
        return frame
    
    def game_trajectory():    
        def get_delta_image(previous_cropped_image, current_cropped_image):
            subtracted_area = previous_cropped_image - current_cropped_image
            subtracted_area = cv2.cvtColor(subtracted_area, cv2.COLOR_BGR2GRAY)
            subtracted_area = cv2.threshold(subtracted_area, 0, 255, cv2.THRESH_BINARY)[1]
            return subtracted_area
        
        previous_frame = get_cropped_image()
        trajectory_image = None
        NUM_ITERATIONS = 100 ## more sophistacted means of breaking the loop here
        for _ in range(NUM_ITERATIONS):
            current_frame = get_cropped_image()
            delta_image = get_delta_image(previous_frame, current_frame)

            if trajectory_image is None:
                trajectory_image = delta_image
            else:
                new_image = trajectory_image | delta_image
                ## TODO more sophisticated test here to see if the delta image has stabilised
                trajectory_image = new_image

        return trajectory_image
    
    def get_simulated_trajectory(desired_angle):                
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
        
        image = get_cropped_image()
        image = np.zeros_like(image)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        start = adjust_start(middle_of(bounding_boxes["white_ball"]))
        length = math.floor(image.shape[1]*1.5) # Trajectory length seems to be around 1.5 times the length of the table

        draw_trajectory(start, desired_angle, length, image)

        return image
    
    # intersect the simulated trajectory and actual trajectory and count ratio of intersected points to number of points in simulated trajectory
    # a score closer to one means that the trajectories are more aligned
    def evaluate_trajectory(simulated_trajectory_image, game_trajectory_image):
        intersected_image = simulated_trajectory_image & game_trajectory_image
        simulated_trajectory_sum = np.sum(simulated_trajectory_image == 255)
        intersected_sum = np.sum(intersected_image == 255)
        if simulated_trajectory_sum == 0:
            return 0
        assert(simulated_trajectory_sum > 0)
        score = intersected_sum / simulated_trajectory_sum
        assert(score >= 0 and score <= 1)
        return score
    ## TODO perf maybe instead of reducing the angle delta we can crop the image for the initial guesses at a low detla
    ## Then for the fine tuning portion we can test on whole frame
    ## This depends on the the slowdown being in the image manipulation code or the trajectory simulation code (numpy a lot of work) (hand coded not so much work)
    ## Then when we get a list of best guesses 
    ## We should only need to wiggle side to side once to narrow down guess to one option
    ## knowing wich direction (anticlockwise or clockwise) and estimated radians per second of around (20)
    ## we should be able to filter down that way because the most common error scenario is a reflection because we are close to the edge
    ## Or we are angled directly to the normal of a border line
    def estimate_current_angle(): 
        DURATION = 2 # seconds
        ESTIMATED_RADIANS_PER_SECOND = 0.2
        THRESHOLD = 0.7
        INITIAL_SIZE = 150
        SECOND_SIZE = 1000000 ## min/max should just result in the full image being returned simpler to code than having a special case in the algorithm
        NUM_SECTORS = 4

        def estimate_with(angles, full_game_image, size):
            small_game_image = get_bounded_image(full_game_image, size)
            best_angle, best_score = angles[0], 0
            for current_angle in angles:
                simulated_trajectory_image = get_simulated_trajectory(current_angle)
                small_simulated_trajectory_iamge = get_bounded_image(simulated_trajectory_image, size)
                score = evaluate_trajectory(small_simulated_trajectory_iamge, small_game_image)
                if score >= best_score:
                    best_angle, best_score = current_angle, score

            return best_angle, best_score
        
        def get_bounded_image(image, size):
            (cx, cy) =  adjust_start(middle_of(bounding_boxes["white_ball"]))
            height, width = image.shape
            start_x = max(0, cx - size)
            start_y = max(0, cy - size)
            end_x = min(cx + size, width - 1)
            end_y = min(cx + size, height - 1)
            return image[start_y:end_y, start_x:end_x]

        def get_angles_to_test(start, end, difference):
            angles = []
            current_angle = start
            while current_angle < end:
                angles.append(current_angle)
                current_angle += difference
            return angles
        
        def move_anticlockwise_a_bit():
            log("Moving anticlockwise for {duration} seconds".format(duration = DURATION))
            anti_clockwise_movement_function(DURATION)
            return DURATION * ESTIMATED_RADIANS_PER_SECOND
        
        def get_anti_clockwise_range(start, radian_range):
            estimated_angle = start + radian_range

            if estimated_angle > 2*math.pi:
                estimated_angle -= (2*math.pi)

            bound = 0.5*radian_range
            difference = 0.01
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
        
        def get_radian_difference(current_angle, target_angle, direction):
            if direction == Direction.ANTI_CLOCKWISE:
                angle, desired = current_angle, target_angle
            else:
                angle, desired = target_angle, current_angle

            if angle < desired:
                return desired - angle
            else:
                return desired + ((2*math.pi) - angle)

        def get_actual_radians_per_second(current_angle, old_angle):
            absolute_difference = get_radian_difference(old_angle, current_angle, Direction.ANTI_CLOCKWISE)
            # difference = current_angle - old_angle
            # absolute_difference =  abs((difference + math.pi) % (2*math.pi) - math.pi)
            return absolute_difference / DURATION
        
        game_trajectory_image = game_trajectory()
        guesses = []
        sector_length = 2*math.pi/NUM_SECTORS
        for sector_num in range(NUM_SECTORS - 1):
            angles_to_test = get_angles_to_test(sector_num*sector_length, (sector_num + 1)*sector_length, 0.01)
            sector_guess = estimate_with(angles_to_test, game_trajectory_image, INITIAL_SIZE)
            if sector_guess[1] >= THRESHOLD:
                guesses.append(sector_guess)

        if len(guesses) == 0:
            log("No angles calcualted to be within the threshold score TODO deal with this case")
            assert(False)

        if len(guesses) == 1:
            log("Only one viable angle calculated just returning that")
            return guesses[0][0]

        ## TODO Filter out angles that are on the boundary line?

        #TODO average estimated radians moved as got keeps playing
        estimated_radians_moved = move_anticlockwise_a_bit()
        game_trajectory_image = game_trajectory()

        new_guesses = []
        for (angle, score) in guesses:
            angles_to_test = get_anti_clockwise_range(angle, estimated_radians_moved)
            estimated_angle, new_score = estimate_with(angles_to_test, game_trajectory_image, SECOND_SIZE)
            new_guesses.append((estimated_angle, new_score, angle))

        new_guesses.sort(reverse=True, key=lambda x:x[1])
        ## TODO handle maybe repeat this in a loop?
        # assert(len(new_guesses) == 1)
        current_angle, old_angle =  new_guesses[0][0], new_guesses[0][2]
        target_angle = angle
        radians_per_second = get_actual_radians_per_second(current_angle, old_angle)

        clockwise_difference = get_radian_difference(current_angle, target_angle, Direction.CLOCKWISE)
        anticlockwise_difference = get_radian_difference(current_angle, target_angle, Direction.ANTI_CLOCKWISE)

        if clockwise_difference < anticlockwise_difference:
            direction = Direction.CLOCKWISE
            abs_radians = clockwise_difference
        else:
            direction = Direction.ANTI_CLOCKWISE
            abs_radians = anticlockwise_difference

        duration = abs_radians / radians_per_second
        if direction == Direction.CLOCKWISE:
            clockwise_movement_function(duration)
        else:
            anti_clockwise_movement_function(duration)
    
    estimate_current_angle()
    # mover = TrajectoryMover(estimate_current_angle, clockwise_movement_function, anti_clockwise_movement_function)
    # mover.move_to_angle(angle, 60)

        

