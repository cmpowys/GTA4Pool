from read_write_memory_process import ReadWriteMemoryProcess
import config
import manualconfig
import conversions as conv
import random
from pool_object import PoolObject
import cv2
import grabscreen
import win32gui
import pickle
import time
import os
import uuid
import pathlib

def get_random_pool_object(pool_object_z):
    def random_range(min, max):
        return min + (max-min)*random.random()

    x = random_range(0,1)
    y = random_range(0,1)
    r1 = random_range(0, 100)
    r2 = random_range(0, 100)
    r3 = random_range(0, 100)

    xy_gamespace = conv.model_space_to_game_space((x,y))

    return PoolObject(xy_gamespace[0], xy_gamespace[1], pool_object_z, r1, r2, r3)

def generate_random_pool_objects(initial_positions):
    return dict([(label, get_random_pool_object(initial_positions[label].z)) for label in initial_positions])

def get_white_ball_ptr(process):
    return process.get_pointer((manualconfig.BASE_ADDRESS + config.WHITE_BALL_PTR_INITIAL_OFFSET_FROM_BASE), offsets=config.WHITE_BALL_PTR_OFFSETS)

def get_ball_from_pointers(label, positions, process):
    ball = positions[label]

    if label == 'white_ball':
        ball_ptr = get_white_ball_ptr(process)
    else:
        ball_ptr = int(manualconfig.POOL_BALL_POINTERS[label], 16)

    return ball, ball_ptr

def write_board_state_to_memory(process, positions):
    for label in positions:
        ball, ball_ptr = get_ball_from_pointers(label, positions, process)
        process.write_pool_ball(ball_ptr, ball)

def get_metadata():
    metadata_path = pathlib.Path(config.TRAINING_METADATA_FILENAME)
    
    if metadata_path.exists():
        metadata_file = open(config.TRAINING_METADATA_FILENAME, 'rb')
        try:
            training_metadata = pickle.load(metadata_file)    
        except:
            training_metadata = dict()  
        metadata_file.close()
        return training_metadata
    else:
        return dict()  

def write_metadata(metadata):
    metadata_file = open(config.TRAINING_METADATA_FILENAME, 'wb')
    pickle.dump(metadata, metadata_file)
    metadata_file.close()

def get_bounding_boxes(positions):
    return dict([(label, conv.get_bounding_box_from_point_in_game_space(positions[label].xy())) for label in positions])

def save_image(directory, img):
    img_id = str(uuid.uuid4())
    filename = os.path.join(directory, img_id) + ".png"
    cv2.imwrite(filename, img)
    return img_id

def generate_training_data(process):
    window_handle = win32gui.FindWindow(None, config.GAME_NAME)
    window_rect = win32gui.GetWindowRect(window_handle)
    metadata = get_metadata()
    pointers = manualconfig.POOL_BALL_POINTERS
    initial_positions = dict((label, process.get_pool_position_object(int(pointers[label], 16))) for label in pointers)
    initial_positions['white_ball'] = process.get_pool_position_object(get_white_ball_ptr(process))

    try:
        print("starting in 3 seconds")
        time.sleep(3)

        for i in range(config.TRAINING_ITERATIONS):
            print(i)
            random_positions = generate_random_pool_objects(initial_positions)
            write_board_state_to_memory(process, random_positions)
            time.sleep(config.TRAINING_ITERATION_DELAY)
            img = grabscreen.grab_screen(window_rect)
            img_id = save_image(config.TRAINING_DIRECTORY, img)
            bounding_boxes = get_bounding_boxes(random_positions)
            metadata[img_id] = bounding_boxes

        write_metadata(metadata)

    finally:
        write_board_state_to_memory(process, initial_positions)


def convert_pool_object_to_model_space(pool_object):
    return conv.game_space_to_model_space(pool_object.xy())

if __name__ == "__main__":
    with ReadWriteMemoryProcess().open_process(config.PROCESS_NAME) as process:
        cv2.namedWindow(config.DISPLAY_WINDOW_NAME)
        cv2.moveWindow(config.DISPLAY_WINDOW_NAME, -2000, 0)
        generate_training_data(process)
        cv2.destroyAllWindows()