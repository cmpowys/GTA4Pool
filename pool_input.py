from time import sleep
import math
import keys

class PoolInput:
    def __init__(self):
        self.keys_obj = keys.Keys()
        self.move = self.keys_obj.directMouse

    def take_shot(self, back_distance=200, forward_distance=400, pause=0.01):
        self.move(dy = back_distance)
        self.wait(pause)
        self.move(dy = -forward_distance)

    def take_shot_scaled(self, scale):
        return self.take_shot(math.floor(200*scale), math.floor(400*scale))

    def move_angle_anticlockwise(self, duration_ms):
        self.hold_spacebar()
        self.keys_obj.directKey("A")
        self.wait(duration_ms)
        self.keys_obj.directKey("A", self.keys_obj.key_release)        
        self.release_spacebar()

    def move_angle_clockwise(self, duration_ms):
        self.hold_spacebar()
        self.keys_obj.directKey("D")
        self.wait(duration_ms)
        self.keys_obj.directKey("D", self.keys_obj.key_release)        
        self.release_spacebar()

    def left_click(self):
        self.move(buttons = self.keys_obj.mouse_lb_press)
        self.wait(0.5)
        self.move(buttons = self.keys_obj.mouse_lb_release)

    def press_key(self, k):
        self.keys_obj.directKey(k)
        self.wait(0.05)
        self.keys_obj.directKey(k, self.keys_obj.key_release)
    
    def press_v(self): self.press_key("V")
    def hold_spacebar(self): self.keys_obj.directKey("SPACE")
    def release_spacebar(self): self.keys_obj.directKey("SPACE", self.keys_obj.key_release)
    def press_a(self): self.press_key("A")
    def press_d(self): self.press_key("D")
    def press_enter(self): self.press_key("RETURN")
    def press_backspace(self): self.press_key("BACK")
    def wait(self, seconds): sleep(seconds)