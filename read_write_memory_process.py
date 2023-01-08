from contextlib import contextmanager
from ReadWriteMemory import ReadWriteMemory
import struct
from pool_object import PoolObject
from pymem import Pymem
import config
import tlhelp32

class ReadWriteMemoryProcess(object):
    def __init__(self):
        self.rwm = ReadWriteMemory()

    @contextmanager
    def open_process(self, process_name):
        try:
            self.process = self.rwm.get_process_by_name(process_name)
            self.process.open()
            self.determine_base_address(process_name)
            yield self
        finally:
            if self.process != None:
                self.process.close()

    def get_process_id(self, process_name):
        with tlhelp32.ProcessSnapshot() as snapshot:
            for idx, process in enumerate(snapshot):
                if process.name == process_name:
                    return process.pid
        assert(False)

    def get_base_address(self, pid, process_name):
        with tlhelp32.ModuleSnapshot(include_32bit=True, pid=pid) as snapshot:
            for idx, module in enumerate(snapshot):
                if module.name == process_name:
                    return module.base_addr
        assert(False)

    def determine_base_address(self, process_name):
        pid = self.get_process_id(process_name) 
        self.base_address = self.get_base_address(pid, process_name)
        
    def get_pointer(self, base_address, offsets):
        return self.process.get_pointer(base_address, offsets)

    def get_int(self, pointer):
        return self.process.read(pointer)

    def get_float(self, pointer):
        int_value = self.get_int(pointer)
        return struct.unpack("@f", struct.pack("@I", int_value))[0]

    def write_int(self, pointer, value):
        self.process.write(pointer, value)

    def write_float(self, pointer, value):
        value_as_integer = struct.unpack("@I", struct.pack("@f", value))[0]
        self.write_int(pointer, value_as_integer)

    def write_pool_ball(self, pointer, pool_ball):
        self.write_float(pointer, pool_ball.r1)
        self.write_float(pointer + 0x4, pool_ball.r2)
        self.write_float(pointer + 0x8, pool_ball.r3)
        self.write_float(pointer + 0x10, pool_ball.x)
        self.write_float(pointer + 0x14, pool_ball.y)
        self.write_float(pointer + 0x18, pool_ball.z)

    def get_pool_position_object(self, pointer):
        r1 = self.get_float(pointer)
        r2 = self.get_float(pointer + 0x4)
        r3 = self.get_float(pointer + 0x8)
        x = self.get_float(pointer + 0x10)
        y = self.get_float(pointer + 0x14)
        z = self.get_float(pointer + 0x18)
        return PoolObject(x, y, z, r1, r2, r3)

    def iterate_over_potential_objects(self, starting_pointer, steps_to_take):
        SIZE_OF_POOL_OBJECT = 0x50

        for i in range(1, steps_to_take):
            yield self.get_pool_position_object(starting_pointer + SIZE_OF_POOL_OBJECT*i), starting_pointer + SIZE_OF_POOL_OBJECT*i
            yield self.get_pool_position_object(starting_pointer - SIZE_OF_POOL_OBJECT*i), starting_pointer - SIZE_OF_POOL_OBJECT*i
 
    def get_white_ball_ptr(self):
        return self.get_pointer((self.base_address + config.WHITE_BALL_PTR_INITIAL_OFFSET_FROM_BASE), offsets=config.WHITE_BALL_PTR_OFFSETS)