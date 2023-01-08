import cv2
import pickle
import os
import config

def main():
    
    metadata = pickle.load(open(config.TRAINING_METADATA_FILENAME, "rb"))
 
    try:
        cv2.namedWindow(config.DISPLAY_WINDOW_NAME)
        for filename in os.listdir(config.TRAINING_DIRECTORY):
            id = filename[:len(filename)-4]
            metadata_entry = metadata[id]
            img = cv2.imread(config.TRAINING_DIRECTORY + "\\" + filename)

            for label in metadata_entry:
                bounding_box = metadata_entry[label]
                cv2.rectangle(img, bounding_box[0], bounding_box[1], (50, 50, 50), 3) 

            cv2.imshow(config.DISPLAY_WINDOW_NAME, img)
            cv2.waitKey(None)

    finally:
        cv2.destroyAllWindows()

 
if __name__ == "__main__":
    main()