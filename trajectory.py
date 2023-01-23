import cv2
import math
import numpy as np

ANGLE_COUNT = 20

class CircularBuffer(object):
    def __init__(self):
        self.array = []
        self.index = 0

    def add(self, element):
        if len(self.array) < ANGLE_COUNT:
            self.array.append(element)
        else:
            self.array[self.index] = element
            self.index = (self.index + 1) % ANGLE_COUNT

class Trajectory(object):
    def __init__(self, center):
        self.center = center
        self.reset()

    def reset(self):
        self.angle_runup = CircularBuffer()
        self.image = None

    def add_delta_image(self, delta_image):
        if self.image is None:
            self.image = delta_image
        else:
            self.image += delta_image
        angle = self.get_estimated_angle()
        self.add_angle(angle)

    def add_angle(self, angle):
        self.angle_runup.add(angle)

    def get_angle(self):
        if (len(self.angle_runup.array) != ANGLE_COUNT):
            return 0

        filtered_angles = np.array(self.angle_runup.array)
        MIN_T = 0.1
        MAX_T = 0.9
        filtered_angles= filtered_angles[(filtered_angles > np.quantile(filtered_angles ,MIN_T)) & (filtered_angles <np.quantile(filtered_angles,MAX_T))].tolist()

        if (len(filtered_angles) < 1):
            return 0

        return np.mean(filtered_angles)

    def get_estimated_angle(self):
        edges = cv2.Canny(self.image, 50, 150, apertureSize=3)        
        lines = cv2.HoughLinesP(
            edges, # Input edge image
            1, # Distance resolution in pixels
            np.pi/180, # Angle resolution in radians
            threshold=100, # Min number of votes for valid line
            minLineLength=5, # Min allowed length of line
            maxLineGap=10 # Max allowed gap between line for joining them
        )

        if lines is None: return 0

        cx, cy = self.center
        min_dist_squared = 1000000
        best_line = cx, cy, cx, cy

        # trying to get a line that starts out closest to white ball
        # this is after we combined the trajectories afer multiple frames
        def get_best_line(x1, y1, x2, y2):
            nonlocal best_line
            nonlocal min_dist_squared
            nonlocal cx, cy

            dist_squred_from_white = (x1 -cx)**2 + (y1 - cy)**2
            if (dist_squred_from_white < min_dist_squared):
                min_dist_squared = dist_squred_from_white
                best_line = x1, y1, x2, y2

        for points in lines:
            (x1,y1, x2, y2) = points[0]
            get_best_line(x1, y1, x2, y2)
            get_best_line(x2, y2, x1, y1)
            

        ## TODO handle edge cases
        (x1, y1, x2, y2) = best_line

        if x2 == x1 or y2 == y1: return 0
        angle = math.atan2((y1 - y2), -(x1 - x2))
        if angle < 0:
            angle += 2*math.pi
        
        return angle