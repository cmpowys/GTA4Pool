import config

def log(string):
    if config.SHOULD_LOG:
        print(string)