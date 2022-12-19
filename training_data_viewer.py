import cv2
import pickle
import os


def main():
    output_directory = r".\\training_images"
    metadatafile = r".\\training_data.pkl"

    metadata = pickle.load(open(metadatafile, "rb"))
    metadata_as_dict = dict()
    for item in metadata:
        metadata_as_dict[item[0]] = item[1]
    
    try:
        winname = "test"
        cv2.namedWindow(winname)
        for filename in os.listdir(output_directory):
            id = filename[:len(filename)-4]
            metadata_entry = metadata_as_dict[id]
            img = cv2.imread(output_directory + "\\" + filename)

            for name in metadata_entry:
                bounding_box = metadata_entry[name]
                cv2.rectangle(img, (bounding_box[0], bounding_box[1]), (bounding_box[2], bounding_box[3]), (50, 50, 50), 3) 

            cv2.imshow(winname, img)
            cv2.waitKey(None)

    finally:
        cv2.destroyAllWindows()

 
if __name__ == "__main__":
    main()