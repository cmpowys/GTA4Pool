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

def main():
    
    metadata = pickle.load(open(config.TRAINING_METADATA_FILENAME, "rb"))
 
    try:
        cv2.namedWindow(config.DISPLAY_WINDOW_NAME)
        for filename in os.listdir(config.TRAINING_DIRECTORY):
            if not filename.endswith(".png"): continue
            id = filename[:len(filename)-4]
            metadata_entry = metadata[id]
            img = cv2.imread(config.TRAINING_DIRECTORY + "\\" + filename)

            for label in metadata_entry:
                bounding_box = metadata_entry[label]
                colour = get_colour_from_label(label)
                draw_circle(img, bounding_box, colour)
                #cv2.rectangle(img, bounding_box[0], bounding_box[1], colour, 1) 

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

def draw_circle(img, bounding_box, colour):
    ((tlx, tly), (brx, bry)) = bounding_box
    dx, dy = (brx - tlx)/2, (bry - tly)/2
    cx, cy = math.floor(tlx + dx), math.floor(tly + dy)
    radius = math.floor((dx + dy)/2)
    cv2.circle(img, (cx, cy), radius, colour)
 
if __name__ == "__main__":
    main()