from learning import Agent
import numpy as np
from bot_logger import log
import cv2
import config

THRESHOLD = 0.01
class TestEnv(object):
    def __init__(self, dims=3):
        self.dims = dims
        self.reset()

    def reset(self):
        self.target_point = np.array([0.1])
        self.current_point = np.random.rand(self.dims)
        return self.current_point
    
    def distance(self):
        dist_squared = 0
        for i,_ in enumerate(self.target_point):
            dist_squared += (self.target_point[i] - self.current_point[i])**2
        return dist_squared ** 0.5
    
    def step(self, new):
        self.current_point = new
        return self.current_point,  -10*self.distance(), self.distance() < THRESHOLD, None 

def learn(): 
    dims = 1
    game = TestEnv(1)
    number_actions = dims
    input_dims = dims
    ##TODO don't hardcode these numbers
    ## TODO batch size should be higher after testing
    agent = Agent(alpha=0.00025, beta=0.00025, input_dims=[input_dims], tau=0.001, batch_size=64, fc1_dims=400, fc2_dims=300, n_actions=number_actions, checkpoint_dir=r".\\learning_checkpoint_test\\")

    try:
        log("Loading model")
        agent.load_models()
    except:
        log("Failed to load model")
        pass
    
    np.random.seed(0)
    score_history = []
    i = 0
    while True:
        j = 0
        done = False
        score = 0
        observations = game.reset()
        while not done:
            action = agent.choose_action(observations)
            new_state, reward, done, info = game.step(action)
            # if j % 100 == 0:
            #     log("Taken action {angle} which resulted in reward {reward} and done = {done}"
            #         .format(angle=list(action), reward=reward, done=done))
            agent.remember(observations, action, reward, new_state, int(done))
            agent.learn()
            score += reward
            observations = new_state
            j += 1
        
        score_history.append(score)
        log("episode " + str(i) + " score " + str(score) + " 100 game average " + str(np.mean(score_history[-100:])))

        if i % 25 == 0:
            agent.save_models() ## time between games are long enough might as well save each game
        i += 1


def play():
    dims = 1
    game = TestEnv(1)
    number_actions = dims
    input_dims = dims
    ##TODO don't hardcode these numbers
    ## TODO batch size should be higher after testing
    agent = Agent(alpha=0.00025, beta=0.00025, input_dims=[input_dims], tau=0.001, batch_size=64, fc1_dims=400, fc2_dims=300, n_actions=number_actions, checkpoint_dir=r".\\learning_checkpoint_test\\")

    log("Loading model")
    agent.load_models()

    done = False
    observations = game.reset()
    num_steps = 0
    while not done:
        action = agent.choose_action(observations)
        print("Action {num_steps} was {action}".format(num_steps=num_steps, action=float(action)))
        new_state, reward, done, info = game.step(action)
        observations = new_state
        num_steps += 1
    print("finished game in {num_steps} steps with number reached {reached}".format(num_steps=num_steps, reached=float(game.target_point)))

if __name__ == "__main__":
    #learn()
    play()
    # while True:
    #     try:
    #         learn()
    #     except Exception as ex:
    #         log("Failed for some reason restarting: " + str(ex))
