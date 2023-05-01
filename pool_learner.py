from learning import Agent
import numpy as np
from bot_logger import log
from pool_game_environment import PoolGameEnvironment
import config

def learn(): 
    game = PoolGameEnvironment()
    number_actions = 1
    input_dims = 3*16
    ##TODO don't hardcode these numbers
    ## TODO batch size should be higher after testing
    agent = Agent(alpha=0.00025, beta=0.00025, input_dims=[input_dims], tau=0.001, batch_size=64, layer1_size=400, layer2_size=300, n_actions=number_actions, checkpoint_dir=config.CHECKPOINT_DIR)

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

if __name__ == "__main__":
    while True:
        try:
            learn()
        except Exception as ex:
            log("Failed for some reason restarting: " + str(ex))