import os
import config
import cv2
# Taken from https://detecto.readthedocs.io/en/latest/index.html
from detecto.core import Model
from detecto import utils, visualize

# for filename in os.listdir(config.TRAINING_DIRECTORY):
#     if not filename.endswith(config.TRAINING_IMAGE_FILE_SUFFIX): continue
#     image = utils.read_image(config.TRAINING_DIRECTORY + "\\" + filename)
#     labels, boxes, scores = model.predict_top(image)
#     visualize.show_labeled_image(image, boxes, labels)

import config
from pytesseract import pytesseract
import win32gui
import grabscreen
import time

# TODO(cpowys) if I just remove the alpha channel from the numpy array this misses balls but if I save the file as png and use the detecto utils module it doesn't ...
# Figure out a way to get the same accuracy without saving the file as a png first
def predict_image(model, screen):
    filename = config.TEMPORARY_IMAGE_NAME
    cv2.imwrite(filename, screen)
    screen = utils.read_image(filename)
    return model.predict_top(screen) ## TODO predict_top misses some balls :(

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

for label in config.POCKET_LABELS:  
    colourings[label] = (100, 100, 100)

def get_colour_from_label(label):
    for colour in colourings:
        if colour in label:
            c = colourings[colour]
            return c[2], c[1], c[0]
    assert(False)


if __name__ == "__main__":
    THRESHOLD = 0.9
    model = Model.load(config.TRAINING_MODEL_FILENAME, config.ALL_MODEL_LABELS)
    window_handle = win32gui.FindWindow(None, config.GAME_NAME)
    rect = win32gui.GetWindowRect(window_handle)
    while True:
        screen = grabscreen.grab_screen(rect)
        labels, boxes, scores = predict_image(model, screen)
        scores_dict = dict()
        bbox_dict = dict()
        for label in config.ALL_MODEL_LABELS:
            scores_dict[label] = 0.0
            bbox_dict[label] = (-1.0, -1.0)
        for index, label in enumerate(labels):
            scores_dict[label] = float(scores[index])
            if scores[index] < THRESHOLD:
                print("Low score for " + labels[index])
            colour = get_colour_from_label(label)
            box = boxes[index]
            bbox = ((round(box[0].item()), round(box[1].item())), (round(box[2].item()), round(box[3].item())))
            bbox_dict[label] = bbox
            if "stripe" in label:
                thickness = 1
            else:
                thickness=3
            cv2.rectangle(screen, bbox[0], bbox[1], colour, thickness)
        cv2.imshow(config.DISPLAY_WINDOW_NAME, screen)
        cv2.waitKey(1)
