from detecto.core import Model, Dataset
import config

def train_model():
    dataset = Dataset(config.TRAINING_DIRECTORY_NAME + "/")
    model = Model(config.POOL_BALL_LABELS + ["white_ball"]) 
    model.fit(dataset)

    #labels, boxes, scores = model.predict(img)

if __name__ == "__main__":
    train_model()