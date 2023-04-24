import cv2
import math
import numpy as np
import config
from detecto import utils

## TODO major refactoring needed
class Trajectory(object):
    def __init__(self, center):
        self.center = center
        self.image = None
        self.zero_frame_count = 0
        self.best_line = None
        self.delta_frames = []

    def draw_trajectory(self, start, angle, length, image):
        if length <= 0:
            return

        border_lines = []
        shape = image.shape[1], image.shape[0]

        border_lines.append((0, 0, shape[0], 0))
        border_lines.append((shape[0], 0, shape[0], shape[1]))
        border_lines.append((shape[0], shape[1], 0, shape[1]))
        border_lines.append((0, shape[1], 0, 0))

        line = self.get_line_with_angle(start, angle, length)

        least_line, least_length, intersected_border = None, 100000, None
        for border_line in border_lines:
            intersection = self.line_intersection(border_line, line)
            if not intersection is None:
                line_to_draw = (line[0], line[1], intersection[0], intersection[1])
                line_length = self.get_line_length(line_to_draw)
                if line_length > 0 and line_length < least_length:
                    least_line, least_length, intersected_border = line_to_draw, line_length, border_line

        if not least_line is None:
            cv2.line(image, (least_line[0], least_line[1]), (least_line[2], least_line[3]), (255, 255, 255), 1)
            remaining_length = length - least_length
            if intersected_border == (0, 0, shape[0], 0):
                reflected_angle = (2*math.pi) - angle
            if intersected_border == (shape[0], 0, shape[0], shape[1]):
                reflected_angle = (math.pi) - angle
            if intersected_border == (shape[0], shape[1], 0, shape[1]):
                reflected_angle = (2*math.pi) - angle
            if intersected_border == (0, shape[1], 0, 0):
                reflected_angle = (math.pi) - angle
            self.draw_trajectory((least_line[2], least_line[3]), reflected_angle, remaining_length, image)
        else: ## assume line ends in pool table
            cv2.line(image, (line[0], line[1]), (line[2], line[3]), (255, 255, 255), 1)

    def get_line_length(self, line):
        (sx, sy, ex, ey) = line
        return ((sx - ex)**2 + (sy - ey)**2)**0.5

    def get_line_with_angle(self, start, angle, length):
        sx, sy = start
        y = -round(length*math.sin(angle))
        x = round(length*math.cos(angle))
        return (sx, sy, sx + x, sy + y)
    
    def line_segments_intersect_with_point(self, line1, line2, point):
        ((x1, y1), (x2, y2)) = line1
        ((x3, y3), (x4, y4)) = line2
        x, y = point

        return (min(x1, x2) <= x <= max(x1, x2) and
                    min(y1, y2) <= y <= max(y1, y2) and
                    min(x3, x4) <= x <= max(x3, x4) and
                    min(y3, y4) <= y <= max(y3, y4))


    def line_intersection(self, line1, line2):
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
        if self.line_segments_intersect_with_point(line1, line2, (x,y)):
            return math.floor(x), math.floor(y)

    def add_delta_image(self, delta_image):
        if delta_image.any():
            self.delta_frames.append(delta_image)
            
        if self.image is None:
            self.image = delta_image
        else:
            new_image = self.image | delta_image
            if not ((new_image - self.image).any()):
                self.zero_frame_count += 1
                if self.zero_frame_count == 10:
                    return True
            self.image = new_image
          

        return False
    ## use edge detection to get sample angles to test
    ## for each angle draw onto an image the trajectory of the pool ball
    ## return the angle which has the most intersection points with the simulated trajectory
    def get_estimated_angle(self):
        edges = cv2.Canny(self.image, 50, 150, apertureSize=3)        
        lines = cv2.HoughLinesP(
            edges, # Input edge image
            1, # Distance resolution in pixels
            np.pi/180, # Angle resolution in radians
            threshold=100, # Min number of votes for valid line
            minLineLength=5, # Min allowed length of line
            maxLineGap=10 # Max allowed gap between line for joining them
        )

        if lines is None: 
            return 0

        cx, cy = self.center
        MIN_DIST = 200
        MAX_LINES = 5
        best_lines = []

        def get_best_line(x1, y1, x2, y2):
            nonlocal best_lines

            def distance(p):
                nonlocal cx
                nonlocal cy
                (x, y) = p

                return  (x -cx)**2 + (y - cy)**2

            def sort_by_distance(p):
                (x1, y1, x2, y2)
                dist_squred_from_white = distance((x1, y1))
                return dist_squred_from_white
            
            dist= distance((x1, y1))**0.5 
            if dist < MIN_DIST:
                best_lines.append((x1, y1, x2, y2))
                best_lines.sort(key = sort_by_distance)
                best_lines = best_lines[:MAX_LINES]

        for points in lines:
            (x1,y1, x2, y2) = points[0]
            get_best_line(x1, y1, x2, y2)
            get_best_line(x2, y2, x1, y1)
            
        max_score, best_angle = -100000, 0,
        for line in best_lines:
            score, angle = self.evaluate_line(line)
            if score > max_score:
                max_score, best_angle = score, angle

        return best_angle
    
    def evaluate_line(self, line):
        LINE_LENGTH = 800
        simulated_trajectory_image = np.zeros_like(self.image)
        angle_of_line = self.angle_of_line(line)
        self.draw_trajectory(self.center, angle_of_line, LINE_LENGTH, simulated_trajectory_image)
        return ((simulated_trajectory_image * self.image > 0).sum()), angle_of_line

    def angle_of_line(self, line):
        (x1, y1, x2, y2) = line
        if x2 == x1 or y2 == y1: 
            return 0
        angle = math.atan2((y1 - y2), -(x1 - x2))
        if angle < 0:
            angle += 2*math.pi
        
        return angle

def predict_image(model, screen):
    filename = config.TEMPORARY_IMAGE_NAME
    cv2.imwrite(filename, screen)
    screen = utils.read_image(filename)
    return model.predict_top(screen)

def get_bounding_boxes(model, screen):
    labels, boxes, scores  = predict_image(model, screen)

    bounding_boxes = dict()
    for index, label in enumerate(labels):
        assert (label in config.ALL_MODEL_LABELS)
        bounding_box_float = boxes[index]
        bounding_box = ((round(bounding_box_float[0].item()), round(bounding_box_float[1].item())), (round(bounding_box_float[2].item()), round(bounding_box_float[3].item())))
        bounding_boxes[label] = bounding_box

    return bounding_boxes
  
def get_delta_image(initial_area, current_area):
    subtracted_area = initial_area - current_area
    subtracted_area = cv2.cvtColor(subtracted_area, cv2.COLOR_BGR2GRAY)
    subtracted_area = cv2.threshold(subtracted_area, 0, 255, cv2.THRESH_BINARY)[1]
    return subtracted_area

def get_white_ball_center(bounding_boxes):
    def middle_of(bounding_box):
        ((tlx, tly), (brx, bry)) = bounding_box
        return tlx + round((brx-tlx)/2), tly + round((bry-tly)/2)

    bounding_box = get_white_ball_bounding_box(bounding_boxes)
    if not bounding_box is None:
        return middle_of(bounding_box)
    
    assert(False)

def get_white_ball_bounding_box(bounding_boxes):
    for label in bounding_boxes:
            if label == "white_ball":
                return bounding_boxes[label]

def get_table_bounding_box(bounding_boxes):
    topleft = None
    bottomright = None

    for label in bounding_boxes:
        if label == "topleft_pocket":
            topleft = bounding_boxes[label]
        if label == "bottomright_pocket":
            bottomright = bounding_boxes[label]
    
    assert (not topleft is None and not bottomright is None)

    return (topleft[0], bottomright[1])

def get_adjusted_white_ball_center(white_ball_center, table_bounding_box):
        ((tlx, tly), (brx, bry)) = table_bounding_box
        cx, cy = white_ball_center
        return cx - tlx, cy - tly

class AngleCalculator(object):
    def __init__(self, model, get_frame_function):
        self.get_frame_function = get_frame_function
        frame = self.get_frame_function()
        bounding_boxes = get_bounding_boxes(model, frame)
        white_ball_center = get_white_ball_center(bounding_boxes)
        self.table_bounding_box = get_table_bounding_box(bounding_boxes)
        self.adjusted_white_ball_center = get_adjusted_white_ball_center(white_ball_center, self.table_bounding_box)

    def get_angle(self):
        trajectory = Trajectory(self.adjusted_white_ball_center)
        previous_screen = crop_to_bounding_box(self.get_frame_function(), self.table_bounding_box)
        while True:
                screen = crop_to_bounding_box(self.get_frame_function(), self.table_bounding_box)
                delta_image = get_delta_image(previous_screen, screen)
                if trajectory.add_delta_image(delta_image):
                    angle = trajectory.get_estimated_angle()
                    return angle
                else:
                    previous_screen = screen

def crop_to_bounding_box(frame, bounding_box):
    ((tlx, tly), (brx, bry)) = bounding_box
    return frame[tly:bry, tlx:brx]

def draw_angle(screen, angle, white_ball_center, colour, line_length):
    cx,cy = white_ball_center
    y = -round(line_length*math.sin(angle))
    x = round(line_length*math.cos(angle))
    end = (cx + x , cy + y)
    cv2.line(screen, white_ball_center, end, colour, 3)