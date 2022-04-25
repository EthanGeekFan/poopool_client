import json
import time
import websocket
from multiprocessing.shared_memory import SharedMemory
from multiprocessing import Process
from multiprocessing import cpu_count
from threading import Thread
import miner
import sys


"""
Structure:

Main Process:
    - Create Shared Memory
    - Create Mining Processes
    - Create Websocket Daemon Thread
    - Terminate Processes on Keyboard Interrupt

Mining Processes:
    - Attach to Shared Memory
    - Start Mining
    - Send Mining Results to Websocket Daemon

WebSocket Daemon Thread:
    - Start Websocket Daemon
    - Send Mining Results to Server
    
"""


connected = False
running = True


class WebsocketDaemon(Thread):
    def __init__(self, url):
        Thread.__init__(self)
        self.ws = websocket.WebSocketApp(url,
                                        on_open=self.on_open,
                                        on_message=self.on_message,
                                        on_error=self.on_error,
                                        on_close=self.on_close)

    def on_open(self):

    def run(self):
        global connected
        global running
        while running:
            if not connected:
                try:
                    ws = websocket.create_connection("ws://


def next_task(ws):
    ws.send(json.dumps({'type': 'task'}))


def on_open(ws):
    print("Connected to server")
    global connected
    connected = True
    next_task(ws)


def on_message(ws, message):
    try:
        data = json.loads(message)
    except json.decoder.JSONDecodeError:
        print("### Error decoding message from Pool Server ###")
        return
    print("Received message: " + str(data))
    try:
        msg_type = data['type']
        if msg_type == 'task':
            global running
            if running:
                print("### Error: Received task while still running ###")
                return
            task = data['task']
            self.nonce_start = int(task['nonce_start'])
            self.nonce_end = int(task['nonce_end'])
            self.block_prefix = task['block_prefix']
            self.block_suffix = task['block_suffix']
            self.target = task['target']
            self.update_task()
            print("Task started")
            self.start()
        elif msg_type == 'newBlock':
            if not self.running:
                print("### Error: Received newBlock while not running ###")
                return
            self.end_task()
            self.next_task()
        # elif msg_type == 'error':
        #     self.end_task()
        #     self.next_task()
        else:
            print("### Error: Unknown message type ###")
            return
    except KeyError:
        print("### Error: Invalid message ###")


def main(url, num_threads=cpu_count()):
    # Create websocket daemon thread
    ws = websocket.WebSocketApp(url,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    # Create Shared Memory
    shared_memory = SharedMemory(create=True, size=1024 * 1024)  # 1MB
    # Create Mining Processes
    mining_processes = []




