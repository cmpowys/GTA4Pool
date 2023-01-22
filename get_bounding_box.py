import cv2
import win32gui
import grabscreen
import config

def locate_bounding_box():
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
                    print("POOL_TABLE_BOUNDING_BOX_IN_PIXEL_SPACE = (({}, {}), ({}, {}))".format(click1[0], click1[1], click2[0], click2[1]))
                    click1 = -1
                    click2 = -1               

        cv2.namedWindow(winname=popupwindowname)
        cv2.setMouseCallback(popupwindowname, on_mouse_event)

        cv2.imshow(popupwindowname, img)
        cv2.waitKey(None)
    finally:
        cv2.destroyAllWindows()

if __name__ == "__main__":
    locate_bounding_box()