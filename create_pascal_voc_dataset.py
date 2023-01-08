import config
import pickle
import os
from PIL import Image

def create_dataset():
    metadata = pickle.load(open(config.TRAINING_METADATA_FILENAME, "rb"))

    for filename in os.listdir(config.TRAINING_DIRECTORY):
        if not filename.endswith(".png"): continue
        id = filename[:len(filename)-4]
        metadata_entry = metadata[id]
        img = Image.open(config.TRAINING_DIRECTORY + "\\" + filename)
        xml = get_xml_data(id, metadata_entry, img)
        save_xml(id, xml)


def save_xml(id, xml):
    xml_file = open(config.TRAINING_DIRECTORY + "\\" + id + ".xml", 'w')
    xml_file.write(xml)
    xml_file.close()

def get_xml_data(id, bounding_boxes, img):
    lines = []
    lines.append('<annotation verified="yes">')
    lines.append('\t<folder>{}</folder>'.format(config.TRAINING_DIRECTORY_NAME))
    lines.append('\t<filename>{}.png</filename>'.format(id))
    lines.append('\t<path>{}/{}.png</path>'.format(config.TRAINING_DIRECTORY_NAME, id))
    lines.append('\t<size>')
    lines.append('\t\t<width>{}</width>'.format(img.width))
    lines.append('\t\t<height>{}</height>'.format(img.height))
    lines.append('\t\t<depth>{}</depth>'.format(4)) # TODO confirm or calculate
    lines.append('\t</size>')
    #TODO is source and size and segmented needed and various other fields (pose difficult etc.)
    for label in bounding_boxes:
        bounding_box = bounding_boxes[label]
        lines.append('\t<object>')
        lines.append('\t\t<name>{}</name>'.format(label))
        lines.append('\t\t<bndbox>')
        lines.append('\t\t\t<xmin>{}</xmin>'.format(bounding_box[0][0]))
        lines.append('\t\t\t<ymin>{}</ymin>'.format(bounding_box[0][1]))
        lines.append('\t\t\t<xmax>{}</xmax>'.format(bounding_box[1][0]))
        lines.append('\t\t\t<ymax>{}</ymax>'.format(bounding_box[1][1]))
        lines.append('\t\t</bndbox>')
        lines.append('\t</object>')
    lines.append('</annotation>')


    return "\n".join(lines)



if __name__ == "__main__":
    create_dataset()