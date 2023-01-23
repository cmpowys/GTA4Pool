from read_write_memory_process import ReadWriteMemoryProcess
import config
import manualconfig
import conversions
import random
from pool_object import PoolObject
import cv2
import grabscreen
import win32gui
import pickle
import time
import os
import uuid

conv = conversions.Conversions.init_from_manual_config()

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

def get_ball_from_pointers(label, positions, process):
    ball = positions[label]
    ball_ptr = get_pool_ball_pointer(process, label)
    return ball, ball_ptr

def write_board_state_to_memory(process, positions):
    for label in positions:
        ball, ball_ptr = get_ball_from_pointers(label, positions, process)
        process.write_pool_ball(ball_ptr, ball)

def write_metadata(directory, img_id, bounding_boxes):
    filename = os.path.join(directory, img_id) + ".pkl"
    metadata_file = open(filename, 'wb')
    pickle.dump(bounding_boxes, metadata_file)
    metadata_file.close()

def get_bounding_boxes(positions):
    return dict([(label, conv.get_bounding_box_from_point_in_game_space(positions[label].xy())) for label in positions])

def save_image(directory, img):
    img_id = str(uuid.uuid4())
    filename = os.path.join(directory, img_id) + ".png"
    cv2.imwrite(filename, img)
    return img_id

def get_pool_ball_pointer(process, label):
    if label == "white_ball": return process.get_white_ball_ptr()
    else: return getattr(manualconfig, label.upper())

def get_pool_ball_pointers(process):
    return dict(((label, get_pool_ball_pointer(process, label)) for label in config.POOL_BALL_LABELS))

def generate_training_data(process):
    window_handle = win32gui.FindWindow(None, config.GAME_NAME)
    window_rect = win32gui.GetWindowRect(window_handle)
    pointers = get_pool_ball_pointers(process)
    initial_positions = dict((label, process.get_pool_position_object(pointers[label])) for label in pointers)

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
            add_pockets_to_bounding_boxes(bounding_boxes)
            write_metadata(config.TRAINING_DIRECTORY, img_id, bounding_boxes)
            pascal_voc_metadata_xml = get_xml_data(config.TRAINING_DIRECTORY, img_id, bounding_boxes, img)
            save_xml(config.TRAINING_DIRECTORY, img_id, pascal_voc_metadata_xml)

    finally:
        write_board_state_to_memory(process, initial_positions)

def add_pockets_to_bounding_boxes(bounding_boxes):
    bounding_boxes["topleft_pocket"] = manualconfig.POCKET_PIXELSPACE_TOPLEFT_BOUNDING_BOX
    bounding_boxes["topmiddle_pocket"] = manualconfig.POCKET_PIXELSPACE_TOPMIDDLE_BOUNDING_BOX
    bounding_boxes["topright_pocket"] = manualconfig.POCKET_PIXELSPACE_TOPRIGHT_BOUNDING_BOX
    bounding_boxes["bottomleft_pocket"] = manualconfig.POCKET_PIXELSPACE_BOTTOMLEFT_BOUNDING_BOX
    bounding_boxes["bottommiddle_pocket"] = manualconfig.POCKET_PIXELSPACE_BOTTOMMIDDLE_BOUNDING_BOX
    bounding_boxes["bottomright_pocket"] = manualconfig.POCKET_PIXELSPACE_BOTTOMRIGHT_BOUNDING_BOX

def convert_pool_object_to_model_space(pool_object):
    return conv.game_space_to_model_space(pool_object.xy())

def save_xml(directory, img_id, xml):
    xml_file = open(directory + "\\" + img_id + ".xml", 'w')
    xml_file.write(xml)
    xml_file.close()

def get_xml_data(directory, img_id, bounding_boxes, img):
    (height, width, depth) = img.shape
    lines = []
    lines.append('<annotation verified="yes">')
    lines.append('\t<folder>{}</folder>'.format(directory))
    lines.append('\t<filename>{}.png</filename>'.format(img_id))
    lines.append('\t<path>{}/{}.png</path>'.format(directory, img_id))
    lines.append('\t<size>')
    lines.append('\t\t<width>{}</width>'.format(width))
    lines.append('\t\t<height>{}</height>'.format(height))
    lines.append('\t\t<depth>{}</depth>'.format(depth))
    lines.append('\t</size>')
    for label in bounding_boxes:
        bounding_box = bounding_boxes[label]
        lines.append('\t<object>')
        lines.append('\t\t<name>{}</name>'.format(label))
        lines.append('\t\t<bndbox>')
        lines.append('\t\t\t<xmin>{}</xmin>'.format(bounding_box[0][0]))
        lines.append('\t\t\t<ymin>{}</ymin>'.format(bounding_box[0][1]))
        lines.append('\t\t\t<xmax>{}</xmax>'.format(bounding_box[1][0]))
        lines.append('\t\t\t<ymax>{}</ymax>'.format(bounding_box[1][1]))
        lines.append('\t\t</bndbox>')
        lines.append('\t</object>')
    lines.append('</annotation>')


    return "\n".join(lines)

if __name__ == "__main__":
    with ReadWriteMemoryProcess().open_process() as process:
        generate_training_data(process)
