import math
from enum import Enum
from bot_logger import log

TWO_PI = 2*math.pi
ANGLE_TOLERANCE = 0.05

class MoveResult(object):
    def __init__(self, angle, min_angle, max_angle, timed_out):
        self.angle = angle
        self.min_angle = min_angle
        self.max_angle = max_angle
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
        self.estimated_radians_per_second = 0.2 ## TODO improve on this estimate as we progress experimentally 0.2 seems about right with the spacebar held

    def move_to_angle(self, desired_angle, timeout):
        log("Attemping to move to angle to {desired_angle}".format(desired_angle = desired_angle))
        self.time_left = timeout ## maybe use an exception based timeout system instead of subtracting duration each time and at least add a maximum duration in case of a math error
        self.desired_angle = desired_angle
        self.get_estimated_angle()

        while self.can_continue():
            self.try_move()
            self.get_estimated_angle()
        return self.result()
    
    def get_estimated_angle(self):
        self.angle = self.angle_calculator.get_angle() ## TODO time taken here not taken into account and this can take a few seconds
        log("Current angle is estimated to be {angle} radians.".format(angle = self.angle))
    
    def result(self):
        has_timed_out = not self.angle_within_tolerance() and self.has_timed_out()
        result = MoveResult(angle = self.angle, min_angle = 0, max_angle = TWO_PI, timed_out = has_timed_out)
        log("Returning result {result}".format(result = result))
        return result

    def move(self, direction, duration):
        log("Moving {direction} for {duration} ms.".format(direction = direction, duration = duration))
        if direction == Direction.CLOCKWISE:
            self.move_clockwise_function(duration)
        else:
            self.move_anticlockwise_function(duration)
        self.time_left -= duration

    def try_move(self): ## TODO for now assume angle calculation is correct we will need to do some error checking (by moving side to side to exclude outliers) and we need to test that we have full 2pi rotation
        ## outliers hopefully only happen when the path falls back onto itself we should design this mover to handle some level of angle errors instead of tyring to get the angle calculation be perfect
        if self.angle < self.desired_angle:
            direction = Direction.ANTI_CLOCKWISE
            abs_radians = self.desired_angle - self.angle
        else:
            direction = Direction.CLOCKWISE
            abs_radians = self.angle - self.desired_angle

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
        return self.time_left < 0

    ## TODO test angle bounds and if angle outside of bounds return early
    def can_continue(self):
        if self.angle_within_tolerance():
            return False
        
        if self.has_timed_out():
            return False
        
        return True