import cv2
import config
import grabscreen
import win32gui
from detecto.core import Model
from detecto import utils
import math
import numpy as np
from trajectory import Trajectory

def get_delta_image(initial_area, current_area, table_bounding_box):
    ((tlx, tly), (brx, bry)) = table_bounding_box
    def trim_area(area):
        return area[tly:bry, tlx:brx]

    subtracted_area = trim_area(initial_area) - trim_area(current_area)
    subtracted_area = cv2.cvtColor(subtracted_area, cv2.COLOR_BGR2GRAY)
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

def draw_angle(screen, angle, white_ball_center, colour):
    LINE_LENGTH = 50
    cx,cy = white_ball_center
    y = -round(LINE_LENGTH*math.sin(angle))
    x = round(LINE_LENGTH*math.cos(angle))
    end = (cx + x , cy + y)
    cv2.line(screen, white_ball_center, end, colour, 3)

def test_line():
    model = Model.load(config.TRAINING_MODEL_FILENAME, config.ALL_MODEL_LABELS)
    cv2.namedWindow(config.DISPLAY_WINDOW_NAME)
    window_handle = win32gui.FindWindow(None, config.GAME_NAME)
    window_rect = win32gui.GetWindowRect(window_handle)
    previous_screen = grabscreen.grab_screen(window_rect)

    bounding_boxes = get_bounding_boxes(model, previous_screen) 
    white_ball_center = get_white_ball_center(bounding_boxes)
    table_bounding_box = get_table_bounding_box(bounding_boxes)
    adjusted_white_ball_center = get_adjusted_white_ball_center(white_ball_center, table_bounding_box)
    trajectory = Trajectory(adjusted_white_ball_center)
    while True:
        screen = grabscreen.grab_screen(window_rect)
        delta_image = get_delta_image(previous_screen, screen, table_bounding_box)
        trajectory.add_delta_image(delta_image)
        previous_screen = screen
        angle = trajectory.get_angle()
        colour = (255, 0, 0)
        draw_angle(previous_screen, angle, white_ball_center, colour)
        cv2.imshow(config.DISPLAY_WINDOW_NAME, previous_screen)
        cv2.waitKey(1)

def get_bounding_boxes(model, screen):
    labels, boxes, scores  = predict_image(model, screen)

    bounding_boxes = dict()
    for index, label in enumerate(labels):
        assert (label in config.ALL_MODEL_LABELS)
        bounding_box_float = boxes[index]
        bounding_box = ((round(bounding_box_float[0].item()), round(bounding_box_float[1].item())), (round(bounding_box_float[2].item()), round(bounding_box_float[3].item())))
        bounding_boxes[label] = bounding_box

    return bounding_boxes

# TODO(cpowys) if I just remove the alpha channel from the numpy array this misses balls but if I save the file as png and use the detecto utils module it doesn't ...
# Figure out a way to get the same accuracy without saving the file as a png first
def predict_image(model, screen):
    filename = config.TEMPORARY_IMAGE_NAME
    cv2.imwrite(filename, screen)
    screen = utils.read_image(filename)
    return model.predict_top(screen) ## TODO predict_top misses some balls :(

if __name__ == "__main__":
    try:
        test_line()
    finally:
        cv2.destroyAllWindows()