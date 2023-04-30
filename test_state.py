from pool_state import State
import grabscreen
import win32gui
import config
from pytesseract import pytesseract
import cv2
import numpy as np

def update_state(state):
    frame = get_frame()
    text = get_text_from_frame(frame)
    state.update_from_text(text)       

def get_frame():
    window_handle = win32gui.FindWindow(None, config.GAME_NAME)
    rect = win32gui.GetWindowRect(window_handle)
    return grabscreen.grab_screen(rect)

def get_text_from_frame(frame):
    frame, gray_frame = preprocess_frame(frame)
    pytesseract.tesseract_cmd = config.PATH_TO_TESSERACT_EXE
    text1 = pytesseract.image_to_string(frame)
    text2 = pytesseract.image_to_string(gray_frame)
    return text1 + text2

def preprocess_frame(frame):
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return frame, gray_frame # some text is better read with colour so we join lol

if __name__ == "__main__":
    state = State()
    while True:
        update_state(state)
        print(state)
else:
    assert(False) # Should only be run as a script