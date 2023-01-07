if __name__ == "__main__":
    import manualconfig
    positions = manualconfig.POOL_BALL_POINTERS

    for label in positions:
        print("{}:{}".format(label, positions[label]))