from enum import Enum
import Levenshtein
from itertools import combinations

class Shot(object):
    def __init__(self, angle, cue_mouse_delta, shot_back_distance, shot_forward_distance):
        self.angle = angle
        self.cue_mouse_delta = cue_mouse_delta
        self.shot_back_distance = shot_back_distance
        self.shot_forward_distance = shot_forward_distance

    def to_array(self):
        return [self.angle] ## TODO include other parameters
    
class CurrentPoolType(Enum):
    UNKNOWN = 0
    SOLID = 1
    STRIPES = 2
    ANY = 3

class PoolState(Enum):
    UNKNOWN = 0
    WAITING = 1
    OVERHEAD = 2
    AIMING = 3
    PENDING_RESTART = 4
    POSITIONING = 5
    NORMAL_VIEW = 6,
    MUST_SHOW_HELP = 7
    RESTART = 8

def get_substrings(string):
    return [string[x:y] for x, y in combinations(range(len(string) + 1), r = 2)]

class FrameText(object):
    def __init__(self, text):
        self.text = text.lower()

    def get_state(self, choices, default, threshold_ratio):
        ratios = {}

        # get the max levenshtein distance ratio for each choice testing all substrings of the frame text
        for choice in choices:
            max_ratio, from_text = 0, ""
            for substring in get_substrings(self.text):
                ratio = Levenshtein.ratio(choice, substring)
                if ratio > max_ratio: max_ratio, from_text = ratio, substring
            ratios[choice] = (max_ratio, from_text)

        # find the choice that gives the highest ratio value that exceeds the past in ratio. If none exceed this ratio we will return the default
        max_ratio, state = 0, default
        for choice in ratios:
            (ratio, _) = ratios[choice]
            if (ratio > threshold_ratio) and ratio > max_ratio:
                max_ratio, state = ratio, choices[choice]

        return state

class Shot(object):
    def __init__(self, angle, cue_mouse_delta, shot_back_distance, shot_forward_distance):
        self.angle = angle
        self.cue_mouse_delta = cue_mouse_delta
        self.shot_back_distance = shot_back_distance
        self.shot_forward_distance = shot_forward_distance

class WinState(Enum):
    GAME_IN_PROGRESS = 0
    WON = 1
    LOST = 2

class State(object):
    def __init__(self):
        self.current_pool_type = CurrentPoolType.UNKNOWN
        self.current_state = PoolState.UNKNOWN
        self.scratched = False
        self.win_state = WinState.GAME_IN_PROGRESS

    def __str__(self):
        return "{state},{type},scratched={scratched},{win}".format(state = self.current_state, type = self.current_pool_type, scratched=self.scratched, win=self.win_state)
    
    def update_from_text(self, text):
        text = FrameText(text)

        THRESHOLD = 0.75

        pool_type_choices = {
            "you may hit any colored ball" : CurrentPoolType.ANY,
            "must hit a striped colored ball" : CurrentPoolType.STRIPES,
            "must hit a solid colored ball" : CurrentPoolType.SOLID
        }

        state_choices = {
            "to position cue ball" : PoolState.POSITIONING,
            "for normal view" : PoolState.OVERHEAD,
            "for overhead view" : PoolState.NORMAL_VIEW,
            "in one motion" : PoolState.AIMING,
            "to show help" :  PoolState.MUST_SHOW_HELP,
            "to play again" : PoolState.RESTART
        }

        scratch_choice = {
            "scratch" : True
        }

        win_state_choices = {
            "you lose" : WinState.LOST,
            "you won" : WinState.WON
        }

        self.current_pool_type = text.get_state(pool_type_choices, self.current_pool_type, THRESHOLD)
        self.current_state = text.get_state(state_choices, PoolState.WAITING, THRESHOLD)
        self.scratched = text.get_state(scratch_choice, False, THRESHOLD)
        self.win_state = text.get_state(win_state_choices, WinState.GAME_IN_PROGRESS, THRESHOLD)
