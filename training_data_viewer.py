import cv2
import pickle
import os
import config
import math

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

def main():
    try:
        cv2.namedWindow(config.DISPLAY_WINDOW_NAME)
        for filename in os.listdir(config.TRAINING_DIRECTORY):
            if not filename.endswith(config.TRAINING_IMAGE_FILE_SUFFIX): continue
            id = filename[:len(filename)-4]
            pkl_filename = id + ".pkl"
            img = cv2.imread(config.TRAINING_DIRECTORY + "\\" + filename)
            bounding_boxes = pickle.load(open(config.TRAINING_DIRECTORY + "\\" + pkl_filename, "rb"))
            for label in bounding_boxes:
                bounding_box = bounding_boxes[label]
                colour = get_colour_from_label(label)
                cv2.rectangle(img, bounding_box[0], bounding_box[1], colour, 1) 

            cv2.imshow(config.DISPLAY_WINDOW_NAME, img)
            cv2.waitKey(None)

    finally:
        cv2.destroyAllWindows()

def get_colour_from_label(label):
    for colour in colourings:
        if colour in label:
            c = colourings[colour]
            return c[2], c[1], c[0]
    assert(False)

if __name__ == "__main__":
    main()