import cv2
from read_write_memory_process import ReadWriteMemoryProcess
import config
import grabscreen
import win32gui
import time
import numpy as np
from conversions import Conversions

def get_bounding_box(prompt, label, choices):
    if label + "_bounding_box" in choices:
        return
    click1 = -1
    click2 = -1
    topleft = None
    bottomright = None
    screen = get_window_screen()
    create_window()

    def on_mouse_event(event, x, y, flags, param):
        nonlocal click1
        nonlocal click2
        nonlocal screen
        nonlocal topleft
        nonlocal bottomright
        
        if event == 1:
            if click1 == -1:
                click1 = (x,y)
            elif click2 == -1:
                click2 = (x,y)
                screen = get_window_screen()
                cv2.rectangle(screen, click1, click2, (100, 100, 100), 3)  
                cv2.imshow(config.DISPLAY_WINDOW_NAME, screen)    
                topleft, bottomright = click1, click2
                click1, click2 = -1, -1
                             
    cv2.imshow(config.DISPLAY_WINDOW_NAME, screen)
    cv2.setMouseCallback(config.DISPLAY_WINDOW_NAME, on_mouse_event)
    print(prompt)
    cv2.waitKey(None)

    if topleft is None or bottomright is None:
        get_bounding_box(prompt, label, choices)
    else:
        choices[label + "_bounding_box"] = (topleft, bottomright)

def get_window_screen():
    window_rect = get_window_rect()
    return grabscreen.grab_screen(window_rect)

def get_window_rect():
    window_handle = win32gui.FindWindow(None, config.GAME_NAME)
    return win32gui.GetWindowRect(window_handle)

def get_window_size():
    (tlx, tly, brx, bry) = get_window_rect()
    return (brx - tlx, bry - tly)

def create_window():
    screen = get_window_screen() #TODO duplicated effort here because we will probably grab screen right after
    height, width, _ = screen.shape
    cv2.namedWindow(config.DISPLAY_WINDOW_NAME)
    cv2.resizeWindow(config.DISPLAY_WINDOW_NAME, width, height)

def move_white_ball_out_of_range(process):
    white_ball = process.get_white_ball_position()
    white_ball.x = 0
    white_ball.y = 0
    process.write_pool_ball(process.get_white_ball_ptr(), white_ball)

def calibrate(process, choices):
    ## TODO
    ## think of a way to force the ai to fail so that we can move the white ball freely sooner
    try:
        if len(choices) == 0:
            input("Play game until you can move white ball freely then press enter>>>")

        white_ball_labels = ["white_pixelspace_topleft", "white_pixelspace_topright", "white_pixelspace_bottomleft"]
        labels = white_ball_labels + ["pocket_pixelspace_topleft", "pocket_pixelspace_topmiddle", "pocket_pixelspace_topright", 
                                    "pocket_pixelspace_bottomleft", "pocket_pixelspace_bottommiddle", "pocket_pixelspace_bottomright"]
        
        for label in labels:
            get_bounding_box("Get bounding box for '{}'".format(label), label, choices)
            if label in white_ball_labels and not (label.replace("pixelspace", "gamespace") in choices):
                position =  process.get_white_ball_position().xy()
                choices[label.replace("pixelspace", "gamespace")] = (position[0], position[1])

        conversions = Conversions(choices["white_gamespace_topleft"], choices["white_gamespace_bottomleft"], choices["white_gamespace_topright"],
                                 choices["white_pixelspace_topleft_bounding_box"], choices["white_pixelspace_bottomleft_bounding_box"], choices["white_pixelspace_topright_bounding_box"]       )

        input("Get game into the starting state and its your turn and press enter>>>")

        get_bounding_box("Get bounding box for pool triangle area", "triangle", choices)
        triangle_bounding_box_gamespace = get_triangle_bounding_box_gamespace(conversions, choices["triangle_bounding_box"])
        determine_pool_object_positions(process, triangle_bounding_box_gamespace,  choices["triangle_bounding_box"], choices)
    finally:
        print(get_config_string(choices))

def get_triangle_bounding_box_gamespace(conversions, triangle_bounding_box):
    (tl, br) = triangle_bounding_box
    return (conversions.pixel_space_to_game_space(tl), conversions.pixel_space_to_game_space(br))
    

def determine_pool_object_positions(process, triangle_bounding_box_gamespace, triangle_bounding_box_pixelspace, choices):
    print("Starting pool movements in 3 seconds focus the game!!!")
    time.sleep(3)
    found = find_objects_within_bounds(process, process.get_white_ball_ptr(), triangle_bounding_box_gamespace[0], triangle_bounding_box_gamespace[1])
    found_len = len(found)
    saved_items = []
    print("Found {} potential objects".format(found_len))

    window_rect = get_window_rect()
    initial_area = get_triangle_sub_image(window_rect, triangle_bounding_box_pixelspace)

    for counter, (ball, pointer) in enumerate(found):
        if counter < config.LOCATE_STARTING_ITERATION: continue
        tmp_ball = ball.copy()
        tmp_ball.x += 3
        
        print("counter=", counter, "total=", found_len)
        process.write_pool_ball(pointer, tmp_ball)

        try:
            time.sleep(config.LOCATE_DELAY)
            new_area = get_triangle_sub_image(window_rect, triangle_bounding_box_pixelspace)

            if areas_changed(initial_area, new_area):
                saved_items.append(pointer)
                print("Saved address", pointer)
        finally:
            process.write_pool_ball(pointer, ball)

    print ("Found {} candidate addresses".format(len(saved_items)))
    print("List of saved addresses :", [hex(addr) for addr in saved_items])
    print("List of saved addresses pointing to x:", [hex(addr+4+4+4+4) for addr in saved_items])

    assert(len(saved_items) >= 15)
    pointer_count = 0
    for ball_pointer in saved_items:
        if pointer_count == 15:
            print("Already have 15 items, discarding rest.")
            break
        ball = process.get_pool_position_object(ball_pointer)
        tmp_ball = ball.copy()
        tmp_ball.x += 0.5
        try:
            process.write_pool_ball(ball_pointer, tmp_ball)
            pointer_count += prompt_for_ball_label(choices, ball_pointer)
        finally:
            process.write_pool_ball(ball_pointer, ball)

    assert (pointer_count == 15)

def prompt_for_ball_label(choices, ball_pointer):
    while True:
        ans = input("Label missing ball>>>")
        if ans == "discard":
            print("Discarding")
            return 0
        elif ans in config.POOL_BALL_LABELS_EXCEPT_WHITE:
            choices[ans] = ball_pointer
            return 1
        else:
            print("Incorrect pall ball label")

def test_bounding_box_predication(conversions, tmp_ball):
    (tl, br) = conversions.get_bounding_box_from_point_in_game_space(tmp_ball.xy())
    screen = get_window_screen()
    cv2.rectangle(screen, tl, br, (100, 100, 100), 2)
    cv2.imshow(config.DISPLAY_WINDOW_NAME, screen)

def get_triangle_sub_image(window_rect, triangle_bounding_box):
    img = grabscreen.grab_screen(window_rect)
    ((tlx, tly), (brx, bry)) = triangle_bounding_box
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

def get_config_string(choices):
    builder = ["Copy config below>>>>>>"]
    for label in choices:
        line = "{} = {}".format(label.upper(), choices[label])
        builder.append(line)
    return "\n".join(builder)

preconfig = """
WHITE_PIXELSPACE_TOPLEFT_BOUNDING_BOX = ((141, 303), (177, 335))
WHITE_GAMESPACE_TOPLEFT = (1472.734375,59.65275955200195)
WHITE_PIXELSPACE_TOPRIGHT_BOUNDING_BOX = ((1118, 300), (1155, 333))
WHITE_GAMESPACE_TOPRIGHT = (1473.03662109375,57.077308654785156)
WHITE_PIXELSPACE_BOTTOMLEFT_BOUNDING_BOX = ((141, 839), (175, 874))
WHITE_GAMESPACE_BOTTOMLEFT = (1471.3182373046875,59.48854446411133)
WHITE_PIXELSPACE_BOTTOMRIGHT_BOUNDING_BOX = ((1121, 842), (1153, 872))
WHITE_GAMESPACE_BOTTOMRIGHT = (1471.6153564453125,56.912269592285156)
POCKET_PIXELSPACE_TOPLEFT_BOUNDING_BOX = ((95, 254), (162, 312))
POCKET_PIXELSPACE_TOPMIDDLE_BOUNDING_BOX = ((617, 244), (680, 301))
POCKET_PIXELSPACE_TOPRIGHT_BOUNDING_BOX = ((1139, 255), (1194, 312))
POCKET_PIXELSPACE_BOTTOMLEFT_BOUNDING_BOX = ((96, 859), (157, 913))
POCKET_PIXELSPACE_BOTTOMMIDDLE_BOUNDING_BOX = ((615, 870), (682, 926))
POCKET_PIXELSPACE_BOTTOMRIGHT_BOUNDING_BOX = ((1137, 856), (1195, 914))
PIXELSPACE_BOUNDING_BOX_ADJUSTMENT = ((613, 555), (648, 587))
TRIANGLE_BOUNDING_BOX = ((887, 499), (1037, 675))
"""

def parse_preconfig(preconfig):
    choices = dict()
    lines = [l.replace(" ", "").split("=") for l in preconfig.splitlines() if l != ""]
    for (label, value) in lines:
        choices[label.lower()] = eval(value)
    return choices

if __name__ == "__main__":
    with ReadWriteMemoryProcess().open_process() as process:
        try:
            choices = parse_preconfig(preconfig)
            calibrate(process, choices)
        finally:
            cv2.destroyAllWindows()