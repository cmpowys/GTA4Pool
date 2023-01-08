from read_write_memory_process import ReadWriteMemoryProcess
import config
import time

def monitor():
    with ReadWriteMemoryProcess().open_process(config.PROCESS_NAME) as process:
        white_ball_ptr = process.get_white_ball_ptr()
        while True:
            white_ball = process.get_pool_position_object(white_ball_ptr)
            print(white_ball)
            time.sleep(1)

if __name__ == "__main__":
    monitor()