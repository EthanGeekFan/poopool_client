import hashlib
from multiprocessing import shared_memory


def mine(prefix, suffix, nonce_start, nonce_end, target, shm_name):
    mem = shared_memory.SharedMemory(name=shm_name)
    nonce = nonce_start
    while mem.buf[0] == 0 and nonce < nonce_end:
        nonce_str = format(nonce, "064x")
        block_with_nonce = prefix + nonce_str + suffix
        blockhash = hashlib.sha256(block_with_nonce.encode('utf-8')).hexdigest()
        if blockhash < target:
            mem.buf[0] = 1
            mem.buf[1:1+len(block_with_nonce)] = block_with_nonce.encode('utf-8')
            mem.buf[1+len(block_with_nonce):1+len(block_with_nonce)+len(blockhash)] = blockhash.encode('utf-8')
            mem.close()
            return
        nonce += 1
    mem.close()
    return

