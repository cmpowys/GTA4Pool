import config
import conversions as conv
from read_write_memory_process import ReadWriteMemoryProcess
import cv2
import win32gui
import grabscreen
import manualconfig

labels = config.POOL_BALL_LABELS + ["white_ball"]

def get_bounding_boxes(process):
    window_handle = win32gui.FindWindow(None, config.GAME_NAME)
    rect = win32gui.GetWindowRect(window_handle)
    img = grabscreen.grab_screen(rect)
    cv2.imshow(config.DISPLAY_WINDOW_NAME, img)

    click1 = -1
    click2 = -1
    label_index = 0
    bounding_boxes = dict()

    def on_mouse_event(event, x, y, flags, param):
        nonlocal click1
        nonlocal click2
        nonlocal img
        nonlocal label_index
        nonlocal bounding_boxes

        if event == 1:
            if click1 == -1:
                click1 = (x,y)
            elif click2 == -1:
                click2 = (x,y)
                cv2.rectangle(img, click1, click2, (100, 100, 100), 1)  
                cv2.imshow(config.DISPLAY_WINDOW_NAME, img)  
                bounding_boxes[labels[label_index]] = (click1, click2)
                click1 = -1
                click2 = -1
                label_index +=1
                if label_index == len(labels):
                    label_index = 0
                    print_bounding_boxes(bounding_boxes, process)
                print("Get bounding box for {}".format(labels[label_index]))

    cv2.setMouseCallback(config.DISPLAY_WINDOW_NAME, on_mouse_event)
    print("Get bounding box for {}".format(labels[label_index]))
    cv2.waitKey(None)


def get_ball_ptr_from_label(process, label):
    if label == "white_ball":
        return process.get_white_ball_ptr()
    return int(manualconfig.POOL_BALL_POINTERS[label], 16)

def print_bounding_boxes(bounding_boxes, process):
    for label in bounding_boxes:
        ((tlx, tly), (brx, bry)) = bounding_boxes[label]
        ball_ptr = get_ball_ptr_from_label(process, label)
        gamespace_position = process.get_pool_position_object(ball_ptr)
        pixel_space_estimate = conv.game_space_to_pixel_space_estimate(gamespace_position.xy())
        tl_adjustment_x = tlx - pixel_space_estimate[0] 
        tl_adjustment_y = tly - pixel_space_estimate[1]
        br_adjustment_x = brx - pixel_space_estimate[0] 
        br_adjustment_y = bry - pixel_space_estimate[1]

        print("PIXELSPACE_ADJUSTMENT_FOR_{} = (({}, {}),({}, {}))".format(label.upper(), tl_adjustment_x, tl_adjustment_y, br_adjustment_x, br_adjustment_y))
    print("")

if __name__ == "__main__":
    cv2.namedWindow(config.DISPLAY_WINDOW_NAME)
    with ReadWriteMemoryProcess().open_process(config.PROCESS_NAME) as process:
        get_bounding_boxes(process)
    cv2.destroyAllWindows()