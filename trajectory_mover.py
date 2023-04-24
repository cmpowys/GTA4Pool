import math
from enum import Enum
from bot_logger import log
import numpy as np

## Static angle calculation struggles along edge and struggles when the ray coincides with itself pi radian reflection
## One idea to improve angle calculation is to draw a simulated path in a high res image then
## perform an image similarity check with the combined path "delta" image
## but as an improvement me we will need to actually move the angle side to side to help predict further?
## the idea is if we have the wrong orientation of the line if we move it clockwise but it moves in the opposite than expected direction
## that would suggest we must use the flipped angle instead
## this flippining happens when the white ball is near an edge because the initial
## ray towards the edge is so small and it appears if the angle is reflected
## Will stick with current algorithm for now

TWO_PI = 2*math.pi
ANGLE_TOLERANCE = 0.05
ADJUSTMENT_ANGLE_TOLERANCE_BY_SPEED = 2
TIME_STEP = 0.5 # seconds
NUM_ITERATIONS = 11

class MoveResult(object):
    def __init__(self, angle, timed_out):
        self.angle = angle
        self.timed_out = timed_out

    def __str__(self):
        if self.timed_out:
            return "Timed out"
        else:
            return "Angle returned = {angle}".format(angle = self.angle)

class Direction(Enum):
    CLOCKWISE = 0
    ANTI_CLOCKWISE = 1

    def __str__(self):
        if self == Direction.CLOCKWISE:
            return "clockwise"
        else:
            return "anticlockwise"

class TrajectoryMover(object):
    def __init__(self, angle_calculator, move_clockwise_function, move_anticlockwise_function, angle_tolerance = ANGLE_TOLERANCE):
        self.angle_calculator = angle_calculator
        self.move_clockwise_function = move_clockwise_function
        self.move_anticlockwise_function = move_anticlockwise_function
        self.angle_tolerance = angle_tolerance
        self.estimated_radians_per_second = 0.2

    def flag_outliers(self, iterations):
        differences = []
        for i in range(1, len(iterations)):
            difference = self.angle_difference(iterations[i-1], iterations[i])
            differences.append(difference)
        iterations = iterations[1:]

        THRESHOLD = 2
        mean = np.mean(differences)
        stddev = np.std(differences)

        if stddev == 0:
            return
        
        num_outliers_removed = 0
        for i,iteration in enumerate(differences):
            z_score = abs(iteration - mean) / stddev
            if z_score > THRESHOLD:
                iterations[i] = None
                num_outliers_removed += 1

        log("Removed {num_outliers_removed} outliers".format(num_outliers_removed = num_outliers_removed))
        return iterations

    def get_first_non_outlier_iteration_index(self, iterations):
        for i, iteration in enumerate(iterations):
            if not iteration is None:
                return i
        assert(False) ## TODO handle

    def improve_radians_per_second_estimate(self, iterations):
        self.estimated_radians_per_second = None ## TODO should we just set initially to 0.2 and keep consistent through out bot process
        skips = 1
        first_iteration_index = self.get_first_non_outlier_iteration_index(iterations) ## TODO wrong need to get last index and then add angle for each None
        previous_angle = iterations[first_iteration_index]
        for i in range(first_iteration_index + 1, len(iterations)):
            if iterations[i] == None:
                skips += 1
            else:
                speed = self.angle_difference(previous_angle, iterations[i]) / (skips * TIME_STEP)
                previous_angle = iterations[i]
                skips = 1
                if self.estimated_radians_per_second is None:
                    self.estimated_radians_per_second = speed
                else:
                    self.estimated_radians_per_second = (self.estimated_radians_per_second + speed) / 2

        log("Estimated radians per second is {current_speed}".format(current_speed = self.estimated_radians_per_second))

    def correct_movement_function_directions(self, iterations):
        assert(self.estimated_radians_per_second != 0) ## TODO handle but should not happen in practice
        if self.estimated_radians_per_second < 0:
            log("We calibrated going anticlockwise instead of clockwise as expected, swapping movement functions")
            self.move_anticlockwise_function, self.move_clockwise_function = self.move_clockwise_function, self.move_anticlockwise_function
            self.estimated_radians_per_second = abs(self.estimated_radians_per_second)

    def angle_difference(self, angle_a, angle_b):
        ## Assuming that the movement is small < pi radians something like that
        difference = angle_b - angle_a
        return (difference + math.pi) % TWO_PI - math.pi

    def get_first_estimated_angle(self, iterations):
        last_valid_angle_index = len(iterations) - 1 - self.get_first_non_outlier_iteration_index(list(reversed(iterations)))
        last_valid_angle = iterations[last_valid_angle_index]
        missing_entries = len(iterations) - 1 - last_valid_angle_index
        self.angle = (last_valid_angle + (missing_entries*self.estimated_radians_per_second*TIME_STEP)) % TWO_PI
        log("Initial guess of angle = {angle}".format( angle = self.angle))

    def calibrate(self):
        log("Calibrating trajectory calculations")
        self.get_estimated_angle()
        iterations = [self.angle]
        for _ in range(NUM_ITERATIONS - 1):
            self.move_anticlockwise_function(TIME_STEP) ## TODO need to check how accurate the timing is maybe higher duration to remove "noise" in timing
            self.get_estimated_angle()
            iterations.append(self.angle)

        iterations = self.flag_outliers(iterations)
        self.improve_radians_per_second_estimate(iterations)
        self.get_first_estimated_angle(iterations)       
        self.correct_movement_function_directions(iterations)

    def move_to_angle(self, desired_angle, timeout):
        log("Attemping to move to angle to {desired_angle}".format(desired_angle = desired_angle))
        self.time_left = timeout ## maybe use an exception based timeout system instead of subtracting duration each time and at least add a maximum duration in case of a math error
        self.desired_angle = desired_angle

        self.calibrate() ## TODO if we fail to calibrate try again a few more times

        while self.can_continue():
            self.try_move()
            self.get_estimated_angle()
            self.adjust_angle_if_necessary()
        return self.result()
    
    def adjust_angle_if_necessary(self):
        ## we have just moved based on a speed calculation so we should be in the ball park
        ## If we are outside of tolerance the angle calculation is busted so we should just leave it 
        ## Other if we are only slightly off we can try to microadjust
        difference = abs(self.angle_difference(self.desired_angle, self.angle))
        if difference > ADJUSTMENT_ANGLE_TOLERANCE_BY_SPEED*self.estimated_radians_per_second:
            self.angle = self.desired_angle
            log("After moving with an estimated speed we are off by {difference} radians. Will leave it as is without microadjustments."
                .format(difference = abs(difference)))

    def get_estimated_angle(self):
        self.angle = self.angle_calculator.get_angle() ## TODO time taken here not taken into account and this can take a few seconds
        log("Current angle is estimated to be {angle} radians.".format(angle = self.angle))
    
    def result(self):
        has_timed_out = not self.angle_within_tolerance() and self.has_timed_out()
        result = MoveResult(angle = self.angle, timed_out = has_timed_out)
        log("Returning result {result}".format(result = result))
        return result

    def move(self, direction, duration):
        log("Moving {direction} for {duration} s.".format(direction = direction, duration = duration))
        if direction == Direction.CLOCKWISE:
            self.move_clockwise_function(duration)
        else:
            self.move_anticlockwise_function(duration)
        self.time_left -= duration
        log("Time left = {time_left}".format(time_left = self.time_left))

    def get_radian_difference(self, direction):
        if direction == Direction.ANTI_CLOCKWISE:
            angle, desired = self.angle, self.desired_angle
        else:
            angle, desired = self.desired_angle, self.angle

        if angle < desired:
            return desired - angle
        else:
            return desired + (TWO_PI - angle)

    def try_move(self):
        clockwise_difference = self.get_radian_difference(Direction.CLOCKWISE)
        anticlockwise_difference = self.get_radian_difference(Direction.ANTI_CLOCKWISE)

        if clockwise_difference < anticlockwise_difference:
            direction = Direction.CLOCKWISE
            abs_radians = clockwise_difference
        else:
            direction = Direction.ANTI_CLOCKWISE
            abs_radians = anticlockwise_difference

        duration = abs_radians / self.estimated_radians_per_second
        
        log("Moving for {duration} seconds because we want to move {abs_radians} radians at an estimated speed of {estimated_radians_per_second}"
                 .format(duration = duration, abs_radians = abs_radians, estimated_radians_per_second=self.estimated_radians_per_second))
        if self.time_left < duration:
            self.time_left = 0
        else:
            self.move(direction, duration)      

    def log(self, string):
        print(string)

    def angle_within_tolerance(self):
        return abs(self.angle - self.desired_angle) < self.angle_tolerance

    def has_timed_out(self):
        return self.time_left <= 0

    def can_continue(self):
        if self.angle_within_tolerance():
            return False
        
        if self.has_timed_out():
            return False
        
        return True