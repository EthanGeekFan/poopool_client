import time
import json
import hashlib
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import miner
import record
import datetime
import sys
from multiprocessing import Process, shared_memory


def canonicalize(message: dict):
    return json.dumps(message, sort_keys=True).replace(" ", "")


def create_block(prev_block, height, thread_count=16):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    pubkey = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    privkey = private_key.private_bytes(serialization.Encoding.Raw,
                                        serialization.PrivateFormat.Raw,
                                        serialization.NoEncryption()).hex()
    print("Mining for private_key: " + privkey)
    print("public_key: " + pubkey)
    coinbase = {
        "height": height,
        "outputs": [
            {
                "pubkey": pubkey,
                "value": 5e13,
            }
        ],
        "type": "transaction",
    }
    coinbase_str = canonicalize(coinbase)
    coinbase_id = hashlib.sha256(coinbase_str.encode()).hexdigest()
    block_prefix = '{"T":"00000002af000000000000000000000000000000000000000000000000000000","created":'
    block_prefix += str(int(time.time()))
    block_prefix += ',"miner":"Ethan","nonce":"'
    block_suffix = '","note":"This is for sale","previd":"'
    block_suffix += prev_block
    block_suffix += '","txids":["'
    block_suffix += coinbase_id
    block_suffix += '"],"type":"block"}'
    mem_size = len(block_prefix) + len(block_suffix) + 64 + 64 + 1
    shm = shared_memory.SharedMemory(create=True, size=mem_size)
    processes = []
    start_time = time.time()
    for i in range(thread_count):
        nonce_start = i * 0x1000000000000000000000000000000000000000000000000000000000000000
        nonce_end = nonce_start + 0x1000000000000000000000000000000000000000000000000000000000000000
        target = "00000002af000000000000000000000000000000000000000000000000000000"
        p = Process(target=miner.mine,
                    args=(block_prefix, block_suffix, nonce_start, nonce_end, target, shm.name))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()
    success = shm.buf[0]
    block = str(shm.buf[1:1+len(block_prefix) + len(block_suffix) + 64].tobytes(), 'utf-8')
    blockhash = str(shm.buf[1+len(block_prefix) + len(block_suffix) + 64:].tobytes(), 'utf-8')
    shm.close()
    shm.unlink()
    end_time = time.time()
    print("Time taken: " + str(end_time - start_time))
    if success:
        print("Success!")
        print(block)
        record.record_block(block, privkey, pubkey, blockhash, height)
        return blockhash
    else:
        print("Failed to mine block")
        return None


def main(threads):
    previd, height = record.resume()
    while True:
        print(f"Mining for block {height} on {previd} with {threads} threads at "
              f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        prev_block = create_block(previd, height, threads)
        if prev_block is not None:
            previd = prev_block
            height += 1
        else:
            break


if __name__ == "__main__":
    if len(sys.argv) > 1:
        thread_count = int(sys.argv[1])
    else:
        thread_count = 16
    main(thread_count)
