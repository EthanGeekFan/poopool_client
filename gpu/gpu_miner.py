import os
import time

import numpy as np
import pyopencl as cl
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
        idx = input("Select a device to use: ")
        try:
            idx = int(idx)
        except:
            idx = 0
        self.dev = self.devices[idx]
        print(' Using device: ' + self.dev.name)
        self.work_group_size = self.dev.max_work_group_size
        print(' Work group size: ' + str(self.work_group_size))
        # Compile the kernel
        kernel_src = ''
        with open(os.path.join(os.path.dirname(__file__), 'sha256_kernel.cl'), 'r') as f:
            kernel_src += f.read()

        kernel_src = kernel_src.encode('ascii')
        kernel_src = kernel_src.replace(b"\r\n", b"\n")
        kernel_src = kernel_src.decode('ascii')

        self.program = cl.Program(self.ctx, kernel_src).build()
        self.kernel = cl.Kernel(self.program, "mine")

    def mine(self, prefix, suffix, nonce_start, nonce_end, shm_name):
        print("GPU starting at nonce: " + format(nonce_start, '064x'))
        mem = SharedMemory(shm_name)
        block_size = len(prefix) + len(suffix) + 64
        payload_word_len = block_size // 4

        prefix_len = len(prefix)
        suffix_len = len(suffix)
        if block_size % 4:
            payload_word_len += 1
        # Prepare buffers
        prefix_buffer = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY, prefix_len)
        cl.enqueue_copy(self.queue, prefix_buffer, prefix.encode('utf-8'))
        suffix_buffer = cl.Buffer(self.ctx, cl.mem_flags.WRITE_ONLY, suffix_len)
        cl.enqueue_copy(self.queue, suffix_buffer, suffix.encode('utf-8'))
        nonce_start_buffer = cl.Buffer(self.ctx, cl.mem_flags.READ_ONLY, 32)
        out_buffer = cl.Buffer(self.ctx, cl.mem_flags.READ_WRITE, 4 * 17)
        payload_mem_buffer = cl.Buffer(self.ctx, cl.mem_flags.READ_WRITE, payload_word_len * 4 * self.work_group_size)

        # Prepare args
        self.kernel.set_arg(0, prefix_buffer)
        self.kernel.set_arg(1, prefix_len.to_bytes(4, 'little'))
        self.kernel.set_arg(2, suffix_buffer)
        self.kernel.set_arg(3, suffix_len.to_bytes(4, 'little'))
        self.kernel.set_arg(4, nonce_start_buffer)
        self.kernel.set_arg(5, out_buffer)
        self.kernel.set_arg(6, payload_mem_buffer)
        for offset in range(nonce_start, nonce_end, self.work_group_size):
            cl.enqueue_copy(self.queue, nonce_start_buffer, offset.to_bytes(32, 'big'))
            cl.enqueue_nd_range_kernel(self.queue, self.kernel, (self.work_group_size,), (self.work_group_size,))
            result = bytearray(4 * 17)
            cl.enqueue_copy(self.queue, result, out_buffer)
            self.queue.finish()

            # Check the result
            if result[-4] == 1:
                # Successfully mined
                nonce = int.from_bytes(bytes(result[:8 * 4]), 'big')
                nonce = format(nonce, '064x')
                blockhash = bytes(result[8 * 4:16 * 4]).hex()
                final_block = prefix + nonce + suffix
                print("GPU found hash: " + blockhash)
                # print("hash[0] = " + format(result[9 * 4], 'x'))
                # print("hash[1] = " + format(result[9 * 4 + 1], 'x'))
                # print("hash[2] = " + format(result[9 * 4 + 2], 'x'))
                # print("hash[3] = " + format(result[9 * 4 + 3], 'x'))
                print("GPU found nonce: " + nonce)
                print("GPU found block: " + final_block)
                mem.buf[0] = 1
                mem.buf[1:1 + block_size] = final_block.encode('utf-8')
                mem.buf[1 + block_size:1 + block_size + len(blockhash)] = blockhash.encode('utf-8')
                mem.close()
                return
            if mem.buf[0] == 1:
                print("GPU failed with iter: " + format(offset - nonce_start, 'x'))
                break
        # If we get here, we didn't find a match
        mem.close()
        return


if __name__ == "__main__":
    gpu = GPUMiner()
    prefix = '{"T":"00000002af000000000000000000000000000000000000000000000000000000","created":1653617251,"miner":"Blockheads PooPool","nonce":"'
    suffix = '","note":"This is for sale. Please contact us if you want to buy it.","previd":"0000000155c933e828eea35e80f11d6fddd8083931351ccc0012e509359004d9","txids":["79b2ea89c88de1d7fee74b45eafb50926a5975cabb9bd85cd293bb6f315624bc"],"type":"block"}'
    nonce_start = 0x0000666666666666666666666666666666666666666666666666666666fccd00
    nonce_end = 0x0000777777777777777777777777777777777777777777777777777777777777
    mem = SharedMemory(create=True, size=len(prefix) + len(suffix) + 64 + 64 + 1)
    start = time.time()
    gpu.mine(prefix, suffix, nonce_start, nonce_end, mem.name)
    end = time.time()
    print("Time taken: " + str(end - start))


