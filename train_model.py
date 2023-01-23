from detecto.core import Model, Dataset
import config

def train_model():
    dataset = Dataset(config.TRAINING_DIRECTORY_NAME + "/")
    model = Model(config.ALL_MODEL_LABELS) 
    model.fit(dataset)
    model.save(config.TRAINING_MODEL_FILENAME)

if __name__ == "__main__":
    train_model()