import json
import time
import websocket
from multiprocessing.shared_memory import SharedMemory
from multiprocessing import Process
from multiprocessing import cpu_count
from threading import Thread
import miner
import sys
from gpu.gpu_miner import GPUMiner


NONCE_SIZE = 64  # bytes
PoW_SIZE = 64  # bytes


class PooPool(object):
    def __init__(self, url, num_threads=cpu_count()):
        print("Initializing...")
        self.url = url
        self.connected = False
        self.memory_size = None
        self.memory = None
        self.processes = None
        self.start_time = None
        self.end_time = None
        self.num_threads = num_threads
        self.nonce_start = None
        self.nonce_end = None
        self.nonce_step = None
        self.block_prefix = None
        self.block_suffix = None
        self.target = None
        self.running = False
        self.task_updated = False
        # self.gpu = GPUMiner()
        print(f"Connecting to pool at {url}, mining with {num_threads} threads")
        self.ws = websocket.WebSocketApp(url,
                                         on_open=self.on_open,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        # self.ws.run_forever()
        self.daemon = Thread(target=self.ws.run_forever)
        self.daemon.start()
        self.routine()

    def routine(self):
        try:
            while not self.connected:
                time.sleep(0.1)
            while self.connected:
                self.next_task()
                while not self.task_updated:
                    time.sleep(0.1)
                self.task_updated = False
                self.start_task()
        except KeyboardInterrupt:
            self.finish()

    def update_task(self):
        self.nonce_step = (self.nonce_end - self.nonce_start) // self.num_threads
        self.memory_size = len(self.block_prefix) + len(self.block_suffix) + NONCE_SIZE + PoW_SIZE + 1
        self.memory = SharedMemory(create=True, size=self.memory_size)
        self.processes = []
        self.task_updated = True

    def next_task(self):
        self.ws.send(json.dumps({'type': 'task'}))

    def start_task(self):
        self.running = True
        self.start_time = time.time()
        for i in range(self.num_threads):
            p = Process(target=miner.mine,
                        args=(self.block_prefix, self.block_suffix, self.nonce_start + i * self.nonce_step,
                              self.nonce_start + (i + 1) * self.nonce_step, self.target, self.memory.name))
            p.start()
            self.processes.append(p)
        # gpu_thread = Thread(target=self.gpu.mine, args=(self.block_prefix, self.block_suffix, self.nonce_start,
        #                                                 self.nonce_end, self.target, self.memory.name))
        # gpu_thread.start()
        for p in self.processes:
            p.join()
        # gpu_thread.join()
        self.end_time = time.time()
        success = self.memory.buf[0]
        block = str(self.memory.buf[1:1 + len(self.block_prefix) + len(self.block_suffix) + NONCE_SIZE].tobytes(),
                    'utf-8')
        blockhash = str(self.memory.buf[1 + len(self.block_prefix) + len(self.block_suffix) + NONCE_SIZE:].tobytes(),
                        'utf-8')
        self.memory.close()
        self.memory.unlink()
        self.running = False
        print("Time taken: " + str(self.end_time - self.start_time))
        if success == 1:
            print("Success!")
            print(block, blockhash)
            self.ws.send(json.dumps({'type': 'submit', 'block': block}))
        else:
            print("Failed to mine block")

    def end_task(self):
        self.memory.buf[0] = 2

    def finish(self):
        self.ws.close()

    def on_open(self, ws):
        print("Connected")
        self.connected = True

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
        except json.decoder.JSONDecodeError:
            print("### Error decoding message from Pool Server ###")
            return
        print("Received message: " + str(data))
        try:
            msg_type = data['type']
            if msg_type == 'task':
                if self.running:
                    print("### Error: Received task while still running ###")
                    return
                task = data['task']
                self.nonce_start = int(task['nonce_start'])
                self.nonce_end = int(task['nonce_end'])
                self.block_prefix = task['block_prefix']
                self.block_suffix = task['block_suffix']
                self.target = task['target']
                self.update_task()
            elif msg_type == 'newBlock':
                if not self.running:
                    print("### Error: Received newBlock while not running ###")
                    return
                self.end_task()
            elif msg_type == 'error':
                self.end_task()
            else:
                print("### Error: Unknown message type ###")
                return
        except KeyError:
            print("### Error: Invalid message ###")

    def on_error(self, ws, error):
        # self.end_task()
        print(error)

    def on_close(self, ws, close_status, close_reason):
        self.end_task()
        self.connected = False
        for p in self.processes:
            p.terminate()
        self.memory.close()
        self.memory.unlink()
        print("### closed ###")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        pool_url = sys.argv[1]
        pool = PooPool(pool_url)
    elif len(sys.argv) > 2:
        pool_url = sys.argv[1]
        threads = int(sys.argv[2])
        pool = PooPool(pool_url, threads)
    else:
        print("Usage: python3 pool.py <pool_url> [threads | default: cpu_count]")
        sys.exit(1)
