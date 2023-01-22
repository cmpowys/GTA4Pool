from read_write_memory_process import ReadWriteMemoryProcess
import config
import time
import conversions as conv 
import cv2
import win32gui
import grabscreen

def monitor():
    window_handle = win32gui.FindWindow(None, config.GAME_NAME)
    rect = win32gui.GetWindowRect(window_handle)

    with ReadWriteMemoryProcess().open_process(config.PROCESS_NAME) as process:
        white_ball_ptr = process.get_white_ball_ptr()
        while True:
            white_ball = process.get_pool_position_object(white_ball_ptr)
            img = grabscreen.grab_screen(rect)
            (p1, p2) = conv.get_bounding_box_from_point_in_game_space("white_ball", white_ball.xy())
            cv2.rectangle(img, p1, p2, (100, 100, 100), 3)
            cv2.imshow(config.DISPLAY_WINDOW_NAME, img)
            cv2.waitKey(50)

if __name__ == "__main__":
    cv2.destroyAllWindows()
    cv2.namedWindow(config.DISPLAY_WINDOW_NAME)
    monitor()
