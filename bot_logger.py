import config
import cv2
import math

def log(string):
    if config.SHOULD_LOG:
        print(string)

def draw_debug_image(image, bounding_boxes, desired_angle):
    draw_trajectory(image, bounding_boxes, desired_angle, 1500, (255, 255, 255))
    draw_pool_balls(image, bounding_boxes)
    cv2.imshow(config.DISPLAY_WINDOW_NAME, image)
    cv2.waitKey(500)
    return

def middle_of(bounding_box):
    ((tlx, tly), (brx, bry)) = bounding_box
    return tlx + ((brx - tlx) // 2), tly + ((bry - tly) // 2)

def radius_of(bounding_box, center):
    SHRINK_FACTOR = 0.75
    ((tlx, tly), (brx, bry)) = bounding_box
    (cx, cy) = center
    return math.floor(SHRINK_FACTOR*(((cx - tlx)**2 + (cy - tly)**2)**0.5))

def draw_trajectory(image, bounding_boxes, angle, length, colour):
    white_ball_bounding_box = bounding_boxes["white_ball"]
    def calculate_table_border_lines():

        def fudge_center(center, radius, dx, dy):
            FUDGE_FACTOR = 0.5
            distance = radius*FUDGE_FACTOR
            cx, cy = center
            return math.floor(cx + (dx*distance)), math.floor(cy + (dy * distance))

        tl_pocket_center = middle_of(bounding_boxes["topleft_pocket"])
        tr_pocket_center = middle_of(bounding_boxes["topright_pocket"])
        bl_pocket_center = middle_of(bounding_boxes["bottomleft_pocket"])
        br_pocket_center = middle_of(bounding_boxes["bottomright_pocket"])

        tl_pocket_center = fudge_center(tl_pocket_center, radius_of(bounding_boxes["topleft_pocket"], tl_pocket_center), 1, 1)
        tr_pocket_center = fudge_center(tr_pocket_center, radius_of(bounding_boxes["topright_pocket"], tr_pocket_center), -1, 1)
        bl_pocket_center = fudge_center(bl_pocket_center, radius_of(bounding_boxes["bottomleft_pocket"], bl_pocket_center), 1, -1)
        br_pocket_center = fudge_center(br_pocket_center, radius_of(bounding_boxes["bottomright_pocket"], br_pocket_center), -1, -1)

        return [
            (tl_pocket_center[0], tl_pocket_center[1], tr_pocket_center[0], tl_pocket_center[1]), ## upper line
            (tr_pocket_center[0], tl_pocket_center[1], tr_pocket_center[0], br_pocket_center[1]), ## right line
            (tr_pocket_center[0], br_pocket_center[1], bl_pocket_center[0], br_pocket_center[1]), ## bottom line
            (bl_pocket_center[0], br_pocket_center[1], bl_pocket_center[0], tl_pocket_center[1])  ## left line
        ]

    def draw_table_border_lines(lines):
        for line in lines:
            cv2.line(image, (line[0], line[1]), (line[2], line[3]), (255, 255, 2555), 1)

    border_lines = calculate_table_border_lines()
    draw_table_border_lines(border_lines)
    _draw_trajectory(middle_of(white_ball_bounding_box), angle, length, image, colour, border_lines)

def draw_pool_balls(image, bounding_boxes):
    colourings = {
        'red' : (255, 0, 0),
        'purple' : (90,0,90), ##800080
        'black' : (0, 0, 0),
        'white' : (255, 255, 255),
        'green' : (0, 255, 0),
        'blue' : (0, 0, 255),
        'brown' : (165,42,42),#A52A2A
        'yellow' : (255, 255, 0),
        'orange' : (255, 165, 0) ##FFA500
    }       

    for label in config.POCKET_LABELS:  
        colourings[label] = (100, 100, 100)

    def get_colour_from_label(label):
        for colour in colourings:
            if colour in label:
                c = colourings[colour]
                return c[2], c[1], c[0]
        assert(False)

    for label in bounding_boxes:
        assert(label in config.ALL_MODEL_LABELS)
        colour = get_colour_from_label(label)
        bounding_box = bounding_boxes[label]
        center = middle_of(bounding_box)
        radius = radius_of(bounding_box, center)
        cv2.circle(image, center, radius, colour)

def _draw_trajectory(start, angle, length, image, colour, border_lines):
    def get_line_length(line):
        (sx, sy, ex, ey) = line
        return ((sx - ex)**2 + (sy - ey)**2)**0.5

    def get_line_with_angle(start, angle, length):
        sx, sy = start
        y = -round(length*math.sin(angle))
        x = round(length*math.cos(angle))
        return (sx, sy, sx + x, sy + y)

    def line_segments_intersect_with_point(line1, line2, point):
        ((x1, y1), (x2, y2)) = line1
        ((x3, y3), (x4, y4)) = line2
        x, y = point

        return (min(x1, x2) <= x <= max(x1, x2) and
                    min(y1, y2) <= y <= max(y1, y2) and
                    min(x3, x4) <= x <= max(x3, x4) and
                    min(y3, y4) <= y <= max(y3, y4))


    def line_intersection(line1, line2):
        line1 = ((line1[0], line1[1]), (line1[2], line1[3]))
        line2 = ((line2[0], line2[1]), (line2[2], line2[3]))
        xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
        ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

        def det(a, b):
            return a[0] * b[1] - a[1] * b[0]

        div = det(xdiff, ydiff)
        if div == 0:
            return None

        d = (det(*line1), det(*line2))
        x = det(d, xdiff) / div
        y = det(d, ydiff) / div
        if line_segments_intersect_with_point(line1, line2, (x,y)):
            return math.floor(x), math.floor(y)

    if length <= 0:
        return

    line = get_line_with_angle(start, angle, length)

    least_line, least_length, intersected_border_index = None, 100000, -1
    for borderline_index, border_line in enumerate(border_lines):
        intersection = line_intersection(border_line, line)
        if not intersection is None:
            line_to_draw = (line[0], line[1], intersection[0], intersection[1])
            line_length = get_line_length(line_to_draw)
            if line_length > 0 and line_length < least_length:
                least_line, least_length, intersected_border_index = line_to_draw, line_length, borderline_index

    if not least_line is None:
        cv2.line(image, (least_line[0], least_line[1]), (least_line[2], least_line[3]), colour, 1)
        remaining_length = length - least_length
        if intersected_border_index == 0:
            reflected_angle = (2*math.pi) - angle
        if intersected_border_index == 1:
            reflected_angle = (math.pi) - angle
        if intersected_border_index == 2:
            reflected_angle = (2*math.pi) - angle
        if intersected_border_index == 3:
            reflected_angle = (math.pi) - angle
        _draw_trajectory((least_line[2], least_line[3]), reflected_angle, remaining_length, image, colour, border_lines)
    else: ## assume line ends in pool table
        cv2.line(image, (line[0], line[1]), (line[2], line[3]), colour, 1)