import numpy as np
import pyopencl as cl
from buffer_structs import BufferStructs

sample = "{\"T\":\"00000002af000000000000000000000000000000000000000000000000000000\",\"created\":1650766178006,\"miner\":\"Blockheads PooPool\",\"nonce\":\"0000666666666666666666666666666666666666666666666666666669a811f8\",\"note\":\"This is for sale. Please contact us if you want to buy it.\",\"previd\":\"00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e\",\"txids\":[\"aa12c1005692cc56c48746cabc2c872c59b7acb6671f56a60b6a491698765963\"],\"type\":\"block\"}"

payloads = [sample] * 100

devices = cl.get_platforms()[0].get_devices()
ctx = cl.Context(devices)
queue = cl.CommandQueue(ctx)

for device in devices:
    print('--------------------------------------------------------------------------')
    print(' Device - Name: ' + device.name)
    print(' Device - Type: ' + cl.device_type.to_string(device.type))
    print(' Device - Compute Units: {0}'.format(device.max_compute_units))
    print(' Device - Max Work Group Size: {0:.0f}'.format(device.max_work_group_size))
    print(' Device - Global memory size: {}'.format(device.global_mem_size))
    print(' Device - Local memory size:  {}'.format(device.local_mem_size))
    print(' Device - Max clock frequency: {} MHz'.format(device.max_clock_frequency))

print('--------------------------------------------------------------------------')

dev = devices[0]
print(' Using device: ' + dev.name)

work_group_size = dev.max_work_group_size
print(' Max Work group size: ' + str(work_group_size))
print()
print(f" Hashing payloads: '{payloads}'")

# Prepare buffer

bufferStructsObj = BufferStructs()
bufferStructsObj.specifySHA2(256, max_in_bytes=1024, max_salt_bytes=0)

# Compile the kernel

kernel_src = bufferStructsObj.code

with open('./sha256.cl', 'r') as f:
    kernel_src += f.read()

kernel_src = kernel_src.encode('ascii')
kernel_src = kernel_src.replace(b"\r\n", b"\n")
kernel_src = kernel_src.decode('ascii')

prg = cl.Program(ctx, kernel_src).build()

buf_arr = bytearray()

chunkSize = min(work_group_size, len(payloads))
for i in range(chunkSize):
    payload = payloads[i]
    payload_len = len(payload)
    buf_arr.extend(payload_len.to_bytes(bufferStructsObj.wordSize, byteorder='little') +
                   payload.encode('ascii') + b'\x00' * (bufferStructsObj.inBufferSize_bytes - payload_len))

pwdim = (chunkSize,)

buf_arr = np.frombuffer(buf_arr, dtype=np.uint32)
result = np.zeros(bufferStructsObj.outBufferSize * chunkSize, dtype=np.uint32)

inbuf = cl.Buffer(ctx, cl.mem_flags.READ_ONLY | cl.mem_flags.COPY_HOST_PTR, hostbuf=buf_arr)
outbuf = cl.Buffer(ctx, cl.mem_flags.WRITE_ONLY, result.nbytes)
prg.hash_main(queue, pwdim, None, inbuf, outbuf)
cl.enqueue_copy(queue, result, outbuf)

out = [bytes(result[i:i + bufferStructsObj.outBufferSize_bytes // bufferStructsObj.wordSize]).hex()
       for i in range(0, len(result), bufferStructsObj.outBufferSize_bytes // bufferStructsObj.wordSize)]

for i in range(0, len(result), bufferStructsObj.outBufferSize_bytes // bufferStructsObj.wordSize):
    print(i // (bufferStructsObj.outBufferSize_bytes // bufferStructsObj.wordSize))


print(f" Hashed to: {out}")
