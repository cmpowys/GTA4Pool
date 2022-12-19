from ReadWriteMemory import ReadWriteMemory
import struct
from contextlib import contextmanager
import time
from collections import defaultdict
import grabscreen
import win32gui
import config
import pickle
import random
import uuid
import os 
import cv2
import math
import numpy as np
from numpy.linalg import inv


BASE_ADDRESS = 0x380000 # TODO work out automatically needs to be set each time program is restarted
# Need to manually get the pointers for the non white ball there is a program that can more efficiently search possible positions in this file to do this
# will also need to pin point the image pixel locations of the top left corner of the white ball and its bottom right corner
# one of the programs in this file helps with that too
# will also need to determine the 4 corners of the pool table using the white ball position in cheat engine so we can convert between game, model and image space

def array(arr):
    return np.array(arr, dtype=np.float32)

class BoardState(object):
    def __init__(self, topleft, bottomright, bottomleft, topright, pool_positions, using_model_space = False):
        self.topleft = array(topleft)
        self.bottomleft = array(bottomleft)
        self.bottomright = array(bottomright)
        self.topright = array(topright)

        if using_model_space:
            self.pool_positions = pool_positions
        else:
            self.pool_positions = [(name, pointer, self.convert_pool_object_from_game_space_to_model_space(position)) for (name, pointer, position) in pool_positions]

    def get_bounding_box_of_object(self, position_in_model_space):
        position_in_image_space = self.convert_point_from_model_space_to_image_space((position_in_model_space.x, position_in_model_space.y))

        topleft = self.white_topleft_in_topleft
        bottomright = self.white_bottomright_in_topleft
        delta_x = bottomright[0] - topleft[0]
        delta_y = bottomright[1] - topleft[1]

        ##TODO not quite right but good enough? probably can be more accurately determined
        ball_top_left = (math.floor(position_in_image_space[0] - (delta_x/3.5) + 1), math.floor(position_in_image_space[1] - (delta_y/3.5)))
        ball_bottom_right = (ball_top_left[0] + delta_x+2, ball_top_left[1] + delta_y+2)
        return (ball_top_left[0], ball_top_left[1], ball_bottom_right[0], ball_bottom_right[1])

    def get_board_bounding_boxes(self):
        bounding_boxes = dict()
        for (name, pointer, position) in self.pool_positions:
            bounding_box = self.get_bounding_box_of_object(position)
            bounding_boxes[name] = bounding_box
        return bounding_boxes

    def draw_state_to_popup(self):
        try:
            window_handle = win32gui.FindWindow(None, config.GAME_NAME)
            rect = win32gui.GetWindowRect(window_handle)
            img = grabscreen.grab_screen(rect)
            popupwindowname = "gta4test"
            cv2.namedWindow(winname=popupwindowname)

            for (name, pointer, position) in self.pool_positions:
                bounding_box = self.get_bounding_box_of_object(position)
                cv2.rectangle(img, (bounding_box[0], bounding_box[1]), (bounding_box[2], bounding_box[3]), (100, 100, 100), 1)

            cv2.imshow(popupwindowname, img)
            cv2.waitKey(None)
        finally:
            cv2.destroyAllWindows()

    def provide_white_ball_bounds(self, white_topleft_in_topleft, white_bottomright_in_topleft, white_topleft_in_bottomright, white_bottomright_in_bottomright):
        self.white_topleft_in_topleft = white_topleft_in_topleft
        self.white_bottomright_in_topleft = white_bottomright_in_topleft
        self.white_topleft_in_bottomright = white_topleft_in_bottomright
        self.white_bottomright_in_bottomright = white_bottomright_in_bottomright

    def generate_random_board_state(self):
        minx = 0
        maxx = 1
        miny = 0
        maxy = 1
        minr = 0
        maxr = 100

        def random_x():
            return minx + (maxx-minx)*random.random()

        def random_y():
            return miny + (maxy-miny)*random.random()

        def random_rotation():
            return minr + (maxr-minr)*random.random()

        def random_position(orig):
            return PoolObjectPosition(random_x(), random_y(), orig.z, random_rotation(), random_rotation(), random_rotation())

        shuffled_positions = [(name, pointer, random_position(orig)) for (name, pointer, orig) in self.pool_positions]

        state =  BoardState(self.topleft, self.bottomright, self.bottomleft, self.topright, shuffled_positions, True)
        state.provide_white_ball_bounds(self.white_topleft_in_topleft, self.white_bottomright_in_topleft, self.white_topleft_in_bottomright,self.white_bottomright_in_bottomright)
        return state

    def convert_pool_object_from_game_space_to_model_space(self, position):
        x, y = self.convert_point_from_game_space_to_model_space((position.x, position.y))
        return PoolObjectPosition(x, y, position.z, position.r1, position.r2, position.r3)

    def convert_pool_object_from_model_space_to_game_space(self, position):
        x, y = self.convert_point_from_model_space_to_game_space((position.x, position.y))
        return PoolObjectPosition(x, y, position.z, position.r1, position.r2, position.r3)

    def get_origin_in_gamespace(self):
        return array(self.topleft)

    def get_gamespace_basis_matrix(self):
        origin = self.get_origin_in_gamespace()
        bottomleft = array(self.bottomleft) - origin
        topright = array(self.topright) - origin
        basis1 = topright
        basis2 = bottomleft 
        return array([[basis1[0], basis2[0]],[basis1[1], basis2[1]]])

    def convert_point_from_game_space_to_model_space(self, point):
        origin = self.get_origin_in_gamespace()
        point = array(point) - origin

        basis_matrix = self.get_gamespace_basis_matrix()
        inv_basis_matrix = inv(basis_matrix)

        result = inv_basis_matrix  @ point

        return result

    def convert_point_from_model_space_to_game_space(self, point):
        x, y = point
        delta_x = self.bottomright[0] - self.topleft[0]
        delta_y = self.bottomright[1] - self.topleft[1]
        game_x = self.topleft[0] + x*delta_x
        game_y = self.topleft[1] + y*delta_y
        return game_x, game_y

    def convert_point_from_model_space_to_image_space(self, point):
        def center(tl, br):
            x = (br[0] -tl[0])/2
            y = (br[1] - tl[1])/2
            return (tl[0] + x, tl[1] + y)

        topleft = center(self.white_topleft_in_topleft, self.white_bottomright_in_topleft)
        bottomright = center(self.white_topleft_in_bottomright, self.white_bottomright_in_bottomright)
        deltax = bottomright[0] - topleft[0]
        deltay = bottomright[1] - topleft[1]

        x = topleft[0] + (point[0]*deltax)
        y = topleft[1] + (point[1]*deltay)
        return math.floor(x),math.floor(y)

    def write_to_process_memory(self, process):
        for (name, pointer, position) in self.pool_positions:
            game_space_position = self.convert_pool_object_from_model_space_to_game_space(position)
            process.write_pool_ball(pointer, game_space_position)

class PoolObjectPosition(object):
    def __init__(self, x, y, z, r1 = 0, r2 = 0, r3 = 1):
        self.x = x
        self.y = y
        self.z = z
        self.r1 = r1
        self.r2 = r2
        self.r3 = r3

    def __str__(self):
        return "position=({},{},{}), rotation=({},{},{})".format(self.x, self.y, self.z, self.r1, self.r2, self.r3)

    def __eq__(self, other):
        if other == None:
            return False
        return self.x == other.x and self.y == other.y and self.z == other.z and self.r1 == other.r1 and self.r2 == other.r2 and self.r3 == other.r3

    def position_equal_within_tolerance(self, other, tolerance):
        dist_squared = (self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2
        if dist_squared < tolerance:
            return True
        return False

    def copy(self):
        return PoolObjectPosition(self.x, self.y, self.z, self.r1, self.r2, self.r3)

red_striped_ball = PoolObjectPosition(1467.694702, 57.24176025,25.32337952)
yellow_solid_ball = PoolObjectPosition(1467.366821, 57.32870865, 24.94081879)
orange_striped_ball = PoolObjectPosition(1470.637939, 53.88607788, 24.98603058)
purple_striped_ball = PoolObjectPosition(1469.857422, 61.09325027, 24.97695923)
black_ball = PoolObjectPosition(1467.5, 59.19515991, 24.75574875)
brown_solid_ball = PoolObjectPosition(1467.501343, 58.48516846, 24.32999992)
green_solid_ball = PoolObjectPosition(1467.501343, 58.59082794, 24.32999992)
orange_solid_ball = PoolObjectPosition(1467.501343, 58.88348007, 24.34210968)
purple_solid_ball = PoolObjectPosition(1467.900024, 58.67934036, 24.32999992)
blue_striped_ball = PoolObjectPosition(1467.630859, 59.06235886, 25.3220787)
yellow_striped_ball = PoolObjectPosition(1467.461304, 58.80718994, 24.75392914)
#blue_solid_ball = PoolObjectPosition()
# solid_red_ball = PoolObjectPosition(1467.501343, 58.67934036, 24.32999992)
# green_striped_ball = PoolObjectPosition(1467.501343, 53.88607788, 24.98603058)

pool_balls = {
    'red_striped_ball' : red_striped_ball,
    'yellow_solid_ball' : yellow_solid_ball,
    'orange_striped_ball' : orange_striped_ball,
    'purple_striped_ball': purple_striped_ball,
    'black_ball' : black_ball,
    'green_solid_ball' : green_solid_ball,
    'orange_solid_ball' : orange_solid_ball,
    'purple_solid_ball': purple_solid_ball,
    'blue_striped_ball' : blue_striped_ball,
    'yellow_striped_ball' : yellow_striped_ball 
}

class ReadWriteMemoryProcess(object):
    def __init__(self):
        self.rwm = ReadWriteMemory()

    @contextmanager
    def open_process(self, process_name):
        try:
            self.process = self.rwm.get_process_by_name(process_name)
            self.process.open()
            yield self
        finally:
            if self.process != None:
                self.process.close()

    def get_pointer(self, base_address, offsets):
        return self.process.get_pointer(base_address, offsets)

    def get_int(self, pointer):
        return self.process.read(pointer)

    def get_float(self, pointer):
        int_value = self.get_int(pointer)
        return struct.unpack("@f", struct.pack("@I", int_value))[0]

    def write_int(self, pointer, value):
        self.process.write(pointer, value)

    def write_float(self, pointer, value):
        value_as_integer = struct.unpack("@I", struct.pack("@f", value))[0]
        self.write_int(pointer, value_as_integer)

    def write_pool_ball(self, pointer, pool_ball):
        self.write_float(pointer, pool_ball.r1)
        self.write_float(pointer + 0x4, pool_ball.r2)
        self.write_float(pointer + 0x8, pool_ball.r3)
        self.write_float(pointer + 0x10, pool_ball.x)
        self.write_float(pointer + 0x14, pool_ball.y)
        self.write_float(pointer + 0x18, pool_ball.z)

    def get_pool_position_object(self, pointer):
        r1 = self.get_float(pointer)
        r2 = self.get_float(pointer + 0x4)
        r3 = self.get_float(pointer + 0x8)
        x = self.get_float(pointer + 0x10)
        y = self.get_float(pointer + 0x14)
        z = self.get_float(pointer + 0x18)

        return PoolObjectPosition(x, y, z, r1, r2, r3)

def get_white_ball_ptr(process):
    return process.get_pointer((BASE_ADDRESS + 0x1215470), offsets=[0x4, 0x38, 0xC, 0x20, 0x44, 0x48, 0x20])

def find_pool_balls(process, white_ball_pointer):
    TOLERANCE = 0.1
    white_ball = process.get_pool_position_object(white_ball_pointer)
    returned_objects = defaultdict(lambda: [])

    def pool_ball_relative_to_white(ball):
        return PoolObjectPosition(ball.x - white_ball.x, ball.y - white_ball.y, ball.z - white_ball.z)

    def add_to_returned_objects(object, pointer):
        for pool_ball_name in pool_balls:
            if pool_ball_relative_to_white(object).position_equal_within_tolerance(pool_ball_relative_to_white(pool_balls[pool_ball_name]), TOLERANCE):
                returned_objects[pool_ball_name].append((object, pointer))
                return

    for object, pointer in iterate_over_potential_objects(process, white_ball_pointer):
        add_to_returned_objects(object, pointer)

    return returned_objects

def find_objects_within_bounds(process, starting_position, topleft, bottomright):
    STEPS_TO_TAKE = 10000

    def between(test, a, b):
        a, b = min(a,b), max(a, b)
        return test >= a and test <= b

    def test(ball):
        return between(ball.x, topleft[0], bottomright[0]) and between(ball.y, topleft[1], bottomright[1]) and between(ball.z, 20, 30)

    return [(ball, pointer) for (ball, pointer) in iterate_over_potential_objects(process, starting_position, STEPS_TO_TAKE) if test(ball)]

def find_pool_object_position(process, starting_position, to_find):
    STEPS_TO_TAKE = 1000
    SIZE_OF_POOL_OBJECT = 0x50
    TOLERANCE = 0.1

    def test(i, mod=1):
        to_test = process.get_pool_position_object(starting_position + mod*SIZE_OF_POOL_OBJECT*i)
        if (to_test.position_equal_within_tolerance(to_find, TOLERANCE)):
            return starting_position + mod*SIZE_OF_POOL_OBJECT*i

    for i in range(STEPS_TO_TAKE):
        found = test(i)
        if found != None:
            return found

        found = test(i, -1)
        if found != None:
            return found

def iterate_over_potential_objects(process, starting_pointer, steps_to_take):
    SIZE_OF_POOL_OBJECT = 0x50

    for i in range(1, steps_to_take):
        yield process.get_pool_position_object(starting_pointer + SIZE_OF_POOL_OBJECT*i), starting_pointer + SIZE_OF_POOL_OBJECT*i
        yield process.get_pool_position_object(starting_pointer - SIZE_OF_POOL_OBJECT*i), starting_pointer - SIZE_OF_POOL_OBJECT*i

def locate_ball_positions_manually(delay=0.5):
    rwmp = ReadWriteMemoryProcess()
    with rwmp.open_process("GTAIV.exe") as process:
        white_ball_ptr = get_white_ball_ptr(process)
        white_ball_position = process.get_pool_position_object(white_ball_ptr)
        found = find_objects_within_bounds(process, white_ball_ptr, (1450,45), (1490, 65))
        found_len = len(found)
        saved_items = []
        print("Found {} potential objects".format(found_len))

        for counter, (ball, pointer) in enumerate(found):
            tmp_ball = ball.copy()
            tmp_ball.x += 0.5
            process.write_pool_ball(pointer, tmp_ball)
            time.sleep(delay)
            print("Move white ball to save position: iteration {} out of {}. {} items saved.".format(counter, found_len, len(saved_items)))
            new_white_ball_position = process.get_pool_position_object(white_ball_ptr)
            if new_white_ball_position != white_ball_position:
                white_ball_position = new_white_ball_position
                saved_items.append(pointer)
                print("You moved the white ball, saving {}.".format(pointer))
            process.write_pool_ball(pointer, ball)
        
        print("List of saved addresses : {}", saved_items)

def generate_training_data():
    ##todo bounds can change
    topleftcorner = (1472.734619,59.6511879)#25.3220787
    bottomleftcorner = (1471.32312, 59.48549652)#, 25.3220787)
    bottomrightcorner = (1471.621216, 56.91326141)
    toprightcorner = (1473.032959,57.07633209)

    whiteballtopleft_in_top_left = (146, 305)
    whiteballbottomright_in_top_left = (177, 334)

    whiteballtopleft_in_bottom_right = (1110,827)
    whiteballbottomright_in_bottom_right = (1141, 856)

    # diagonal_length = ((whiteballbottomright[0] - whiteballtopleft[0]) ** 2 + (whiteballbottomright[1] - whiteballtopleft[1])**2)**0.5
    # ballradius_in_image_space = diagonal_length / 2

    pointers = {
        'white' : 0x816E8A0,
        'black' : 0x81409f0,
        'red_striped_ball' : 0x8168e50,
        'brown_solid_ball' : 0x817b550,
        'blue_striped_ball' : 0x817beb0,
        'green_striped_ball' : 0x817ce50,
        'blue_solid_ball' : 0x817d1c0,
        'purple_striped_ball' : 0x81585f0,
        'brown_striped_ball': 0x8152600,
        'red_solid_ball' : 0x8190720,
        'green_solid_ball' : 0x81465d0,
        'yellow_solid_ball': 0x81422a0,
        'yellow_striped_ball' : 0x8140a40,
        'purple_solid_ball' :  0x819ea50,
        'orange_solid_ball' : 0x819eaa0,
        'orange_striped_ball' : 0x81a9540
    }

    rwmp = ReadWriteMemoryProcess()
    with rwmp.open_process("GTAIV.exe") as process:
        initial_positions = [(name, pointers[name], process.get_pool_position_object(pointers[name])) for name in pointers]
        board_state = BoardState(topleftcorner, bottomrightcorner, bottomleftcorner, toprightcorner, initial_positions)
        board_state.provide_white_ball_bounds(whiteballtopleft_in_top_left, whiteballbottomright_in_top_left,whiteballtopleft_in_bottom_right,whiteballbottomright_in_bottom_right)

        try:
            output_directory = r".\\training_images"
            metadatafile = r".\\training_data.pkl"
            training_metadata = []
            window_handle = win32gui.FindWindow(None, config.GAME_NAME)
            rect = win32gui.GetWindowRect(window_handle)
            
            for i in range(10):
                random_board = board_state.generate_random_board_state()
                random_board.write_to_process_memory(process)
                bounding_boxes = board_state.get_board_bounding_boxes()
                img = grabscreen.grab_screen(rect)
                img_id = save_image(output_directory, img)
                training_metadata.append((img_id, bounding_boxes))
                time.sleep(2)

            pickle.dump(training_metadata, open(metadatafile, "wb"))
        finally:
            for (name, pointer, position) in initial_positions:
                process.write_pool_ball(pointer, position)

def save_image(directory, img):
    img_id = str(uuid.uuid4())
    filename = os.path.join(directory, img_id) + ".png"
    cv2.imwrite(filename, img)

    return img_id

def get_image_space_coords():
    try:
        window_handle = win32gui.FindWindow(None, config.GAME_NAME)
        rect = win32gui.GetWindowRect(window_handle)
        img = grabscreen.grab_screen(rect)

        click1 = -1
        click2 = -1
        popupwindowname = "gta4test"

        def on_mouse_event(event, x, y, flags, param):
            nonlocal click1
            nonlocal click2
            nonlocal popupwindowname
            nonlocal img
            if event == 1:
                if click1 == -1:
                    click1 = (x,y)
                elif click2 == -1:
                    click2 = (x,y)
                    cv2.rectangle(img, click1, click2, (100, 100, 100), 3)  
                    cv2.imshow(popupwindowname, img)  
                    print('Topleft of whiteball = {}, Bottomright of whiteball = {}'.format(click1, click2))                

        cv2.namedWindow(winname=popupwindowname)
        cv2.setMouseCallback(popupwindowname, on_mouse_event)

        cv2.imshow(popupwindowname, img)
        cv2.waitKey(None)
    finally:
        cv2.destroyAllWindows()

def main():
    #get_image_space_coords()
    generate_training_data()
    # #locate_ball_positions_manually()


if __name__ == "__main__":
    main()