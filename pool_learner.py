from learning import Agent
import numpy as np
from bot_logger import log
from pool_game_environment import PoolGameEnvironment
import config

def learn(): 
    game = PoolGameEnvironment()
    number_actions = 1
    input_dims = 3*16 + 1 #16 for each x,y coord of a ball and if its present plus 1 for the current pool type (solid or stripes or any)
    ##TODO don't hardcode these numbers
    ## TODO batch size should be higher after testing
    agent = Agent(checkpoint_dir=config.CHECKPOINT_DIR,alpha=0.00025, beta=0.00025, input_dims=[input_dims], tau=0.001, batch_size=64, fc1_dims=400, fc2_dims=300, n_actions=number_actions)
    
    def attempt():
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
            done = False
            score = 0
            observations = game.reset()
            while not done:
                action = agent.choose_action(observations)
                new_state, reward, done, info = game.step(action)
                log("Taken action {angle} which resulted in reward {reward} and done = {done}"
                    .format(angle=float(action), reward=reward, done=done))
                agent.remember(observations, action, reward, new_state, int(done))
                agent.learn()
                score += reward
                observations = new_state
            
            score_history.append(score)
            log("episode " + str(i) + " score " + str(score) + " 100 game average " + str(np.mean(score_history[-100:])))

            agent.save_models() ## time between games are long enough might as well save each game
            i += 1

    while True:
        try:
            attempt()
        except Exception as ex:
            log("Failed for some reason restarting: " + str(ex))

if __name__ == "__main__":
    learn()
