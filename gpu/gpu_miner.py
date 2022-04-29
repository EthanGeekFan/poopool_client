import os
import numpy as np
import pyopencl as cl
from pyopencl.tools import PooledBuffer
from gpu.buffer_structs import BufferStructs
from multiprocessing.shared_memory import SharedMemory

max_block_size = 1024  # 1KB


class GPUMiner:
    def __init__(self):
        self.buffer_structs = BufferStructs()
        self.buffer_structs.specifySHA2(256, max_in_bytes=max_block_size, max_salt_bytes=0)
        self.devices = cl.get_platforms()[0].get_devices()
        self.ctx = cl.Context(self.devices)
        self.queue = cl.CommandQueue(self.ctx)
        self.dev = self.devices[0]
        for device in self.devices:
            print('--------------------------------------------------------------------------')
            print(' Device - Name: ' + device.name)
            print(' Device - Type: ' + cl.device_type.to_string(device.type))
            print(' Device - Compute Units: {0}'.format(device.max_compute_units))
            print(' Device - Max Work Group Size: {0:.0f}'.format(device.max_work_group_size))
            print(' Device - Global memory size: {}'.format(device.global_mem_size))
            print(' Device - Local memory size:  {}'.format(device.local_mem_size))
            print(' Device - Max clock frequency: {} MHz'.format(device.max_clock_frequency))
        print('--------------------------------------------------------------------------')
        print(' Using device: ' + self.dev.name)
        self.work_group_size = self.dev.max_work_group_size
        print(' Work group size: ' + str(self.work_group_size))
        # Compile the kernel
        kernel_src = self.buffer_structs.code
        with open(os.path.join(os.path.dirname(__file__), 'sha256.cl'), 'r') as f:
            kernel_src += f.read()

        kernel_src = kernel_src.encode('ascii')
        kernel_src = kernel_src.replace(b"\r\n", b"\n")
        kernel_src = kernel_src.decode('ascii')

        self.program = cl.Program(self.ctx, kernel_src).build()

    def mine(self, prefix, suffix, nonce_start, nonce_end, target, shm_name):
        mem = SharedMemory(shm_name)
        block_size = len(prefix) + len(suffix) + 64
        for offset in range(nonce_start, nonce_end, self.work_group_size):
            # Create the buffers
            raw_buffer = bytearray()
            if not mem.buf[0] == 0:
                # new block
                break
            for i in range(self.work_group_size):
                nonce_str = format(offset + i, "064x")
                block_with_nonce = prefix + nonce_str + suffix
                size = block_size
                raw_buffer.extend(size.to_bytes(self.buffer_structs.wordSize, byteorder='little') +
                                  block_with_nonce.encode('utf-8') +
                                  b'\x00' * (self.buffer_structs.inBufferSize_bytes - size))
            raw_buffer = np.frombuffer(raw_buffer, dtype=np.uint32)
            result_buffer = np.zeros(self.buffer_structs.outBufferSize * self.work_group_size, dtype=np.uint32)
            in_buffer_gpu = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=raw_buffer)
            out_buffer_gpu = cl.Buffer(self.ctx, cl.mem_flags.WRITE_ONLY, result_buffer.nbytes)
            # Execute the kernel
            self.program.hash_main(self.queue, (self.work_group_size,), None, in_buffer_gpu, out_buffer_gpu)
            # Copy the result back to the host
            cl.enqueue_copy(self.queue, result_buffer, out_buffer_gpu)
            # Check the result
            hash_word_size = self.buffer_structs.outBufferSize_bytes // self.buffer_structs.wordSize
            for i in range(0, len(result_buffer), hash_word_size):
                blockhash = bytes(result_buffer[i:i + hash_word_size]).hex()
                if blockhash < target:
                    mem.buf[0] = 1
                    final_block = prefix + format(offset + (i // hash_word_size), "064x") + suffix
                    mem.buf[1:1 + block_size] = final_block.encode('utf-8')
                    mem.buf[1 + block_size:1 + block_size + len(blockhash)] = blockhash.encode('utf-8')
                    print("GPU found block: " + final_block)
                    print("GPU found hash: " + blockhash)
                    print("GPU found nonce: " + format(offset + (i // hash_word_size), "064x"))
                    mem.close()
                    return
        # If we get here, we didn't find a match
        mem.close()
        return



