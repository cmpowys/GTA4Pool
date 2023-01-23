import os
import config

# Taken from https://detecto.readthedocs.io/en/latest/index.html
from detecto.core import Model
from detecto import utils, visualize

model = Model.load(config.TRAINING_MODEL_FILENAME, config.ALL_MODEL_LABELS)
for filename in os.listdir(config.TRAINING_DIRECTORY):
    if not filename.endswith(config.TRAINING_IMAGE_FILE_SUFFIX): continue
    image = utils.read_image(config.TRAINING_DIRECTORY + "\\" + filename)
    labels, boxes, scores = model.predict_top(image)
    visualize.show_labeled_image(image, boxes, labels)