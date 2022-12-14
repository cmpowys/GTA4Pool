from read_write_memory_process import ReadWriteMemoryProcess
import time
import manualconfig
import config
import cv2
import grabscreen
import win32gui
import numpy as np

def locate_ball_positions_manually():
    window_handle = win32gui.FindWindow(None, config.GAME_NAME)
    window_rect = win32gui.GetWindowRect(window_handle)
    rwmp = ReadWriteMemoryProcess()

    with rwmp.open_process(config.PROCESS_NAME) as process:
        white_ball_ptr = process.get_white_ball_ptr()
        found = find_objects_within_bounds(process, white_ball_ptr, manualconfig.LOCATE_TOPLEFT_BOUND, manualconfig.LOCATE_BOTTOMRIGHT_BOUND)
        found_len = len(found)
        saved_items = []
        print("Found {} potential objects".format(found_len))

        initial_area = get_triangle_sub_image(window_rect)

        for counter, (ball, pointer) in enumerate(found):
            if counter < config.LOCATE_STARTING_ITERATION: continue
            tmp_ball = ball.copy()
            tmp_ball.x += 3
            
            print("counter=", counter, "total=", found_len)
            process.write_pool_ball(pointer, tmp_ball)
            time.sleep(config.LOCATE_DELAY)
            new_area = get_triangle_sub_image(window_rect)

            if areas_changed(initial_area, new_area):
                saved_items.append(pointer)
                print("Saved address", pointer)

            process.write_pool_ball(pointer, ball)

        print ("Found {} candidate addresses".format(len(saved_items)))
        print("List of saved addresses :", [hex(addr) for addr in saved_items])
        print("List of saved addresses pointing to x:", [hex(addr+4+4+4+4) for addr in saved_items])

        assert(len(saved_items) >= 15)
        labeled_pointers = dict()
        for ball_pointer in saved_items:
            ball = process.get_pool_position_object(ball_pointer)
            tmp_ball = ball.copy()
            tmp_ball.x += 0.5
            process.write_pool_ball(ball_pointer, tmp_ball)

            while True:
                ans = input("Enter discard to discard, quit to quit, otherwise provide_label")
                process.write_pool_ball(ball_pointer, ball)
                if ans == "discard": break
                if ans == "quit": return
                if ans in config.POOL_BALL_LABELS:
                    labeled_pointers[ans] = hex(ball_pointer)
                    break
                print("Incorrect label must be one of {}, try again".format(config.POOL_BALL_LABELS))

        assert(len(labeled_pointers) == 15)
        print(labeled_pointers)



def get_triangle_sub_image(window_rect):
    img = grabscreen.grab_screen(window_rect)
    ((tlx, tly), (brx, bry)) = manualconfig.POOL_TRIANGLE_BOUNDING_BOX
    img = img[tly:bry, tlx:brx]
    return img

def areas_changed(initial_area, current_area):
    subtracted_area = initial_area - current_area
    subtracted_area = cv2.cvtColor(subtracted_area, cv2.COLOR_BGR2GRAY)
    return np.average(subtracted_area) > config.LOCATE_AREA_THRESHOLD

def find_objects_within_bounds(process, starting_position, topleft, bottomright):
    STEPS_TO_TAKE = 10000

    def between(test, a, b):
        a, b = min(a,b), max(a, b)
        return test >= a and test <= b

    def test(ball):
        return between(ball.x, topleft[0], bottomright[0]) and between(ball.y, topleft[1], bottomright[1]) and between(ball.z, 20, 30)

    return [(ball, pointer) for (ball, pointer) in process.iterate_over_potential_objects(starting_position, STEPS_TO_TAKE) if test(ball)]

if __name__ == "__main__":
    locate_ball_positions_manually()
