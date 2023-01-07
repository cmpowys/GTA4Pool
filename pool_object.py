class PoolObject(object):
    def __init__(self, x, y, z, r1, r2, r3):
        self.x = x
        self.y = y
        self.z = z
        self.r1 = r1
        self.r2 = r2
        self.r3 = r3

    def copy(self):
        return PoolObject(self.x, self.y, self.z, self.r1, self.r2, self.r3)

    def __str__(self):
        return "position=({},{},{}), rotation=({},{},{})".format(self.x, self.y, self.z, self.r1, self.r2, self.r3)

    def __eq__(self, other):
        if other == None:
            return False
        return self.x == other.x and self.y == other.y and self.z == other.z and self.r1 == other.r1 and self.r2 == other.r2 and self.r3 == other.r3