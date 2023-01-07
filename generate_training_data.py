from read_write_memory_process import ReadWriteMemoryProcess
import config
import manualconfig
import conversions as conv
import random
from pool_object import PoolObject
import cv2
import grabscreen
import win32gui

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

def generate_training_data(process):
    window_handle = win32gui.FindWindow(None, config.GAME_NAME)
    window_rect = win32gui.GetWindowRect(window_handle)
    img = grabscreen.grab_screen(window_rect)

    pointers = manualconfig.POOL_BALL_POINTERS
    initial_positions = dict((label, process.get_pool_position_object(int(pointers[label], 16))) for label in pointers)
    
    for label in initial_positions:
        ball = initial_positions[label]
        position = [ball.x, ball.y]
        bbox = conv.get_bounding_box_from_point_in_game_space(position)
        #print(position, bbox)
        cv2.rectangle(img, bbox[0], bbox[1], (100, 100, 100), 3)
        #print (bbox)
        #cv2.circle(img, bbox, 10, (100, 100, 100))
    cv2.imshow(config.DISPLAY_WINDOW_NAME, img)
    cv2.waitKey(None)

    
def convert_pool_object_to_model_space(pool_object):
    return conv.game_space_to_model_space((pool_object.x, pool_object.y))

if __name__ == "__main__":
    with ReadWriteMemoryProcess().open_process(config.PROCESS_NAME) as process:
        cv2.namedWindow(config.DISPLAY_WINDOW_NAME)
        generate_training_data(process)
        cv2.destroyAllWindows()