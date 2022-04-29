#!/usr/bin/python3
# -*- coding: utf-8 -*-
# (c) B. Kerler 2018-2021
# MIT License
'''
    Provides a class for filling in my buffer_structs_template.cl
'''

import os
import re

# Read the template in
# template = ""
with open(os.path.join(os.path.dirname(__file__), "buffer_structs_template.cl"), "r") as rf:
    template = rf.read()


def ceil_to_mult(n, k):
    return n + ((-n) % k)


class BufferStructs:
    def __init__(self):
        self.hashDigestSize_bits = None
        self.hashBlockSize_bits = None
        self.ctBufferSize_bytes = None
        self.saltBufferSize = None
        self.outBufferSize = None
        self.saltBufferSize_bytes = None
        self.inBufferSize = None
        self.outBufferSize_bytes = None
        self.inBufferSize_bytes = None
        self.code = ""
        self.wordSize = 4
        
    def set_max_buffer_sizes(self, max_in_bytes, max_out_bytes, max_salt_bytes=32, max_ct_bytes=0):
        # Ensure each are a multiple of 4
        max_in_bytes += (-max_in_bytes % self.wordSize)
        max_out_bytes += (-max_out_bytes % self.wordSize)
        max_salt_bytes += (-max_salt_bytes % self.wordSize)

        self.inBufferSize_bytes = max_in_bytes
        self.outBufferSize_bytes = max_out_bytes
        self.saltBufferSize_bytes = max_salt_bytes
        self.inBufferSize = (max_in_bytes + 3) // self.wordSize
        self.outBufferSize = (max_out_bytes + 3) // self.wordSize
        self.saltBufferSize = (max_salt_bytes + 3) // self.wordSize
        self.ctBufferSize_bytes = max_ct_bytes

    def specify_hash_sizes(self, hash_block_size_bits, hash_digest_size_bits):
        self.hashBlockSize_bits = hash_block_size_bits
        self.hashDigestSize_bits = hash_digest_size_bits

    def set_buffer_sizes_for_hashing(self, hash_max_num_blocks):
        self.set_max_buffer_sizes(((self.hashBlockSize_bits + 7) // 8) * hash_max_num_blocks,
                                  (self.hashDigestSize_bits + 7) // 8,
                                  0)

    def fill_template(self):
        rep = { "<hashBlockSize_bits>": str(self.hashBlockSize_bits),
                "<hashDigestSize_bits>" : str(self.hashDigestSize_bits),
                "<inBufferSize_bytes>" : str(self.inBufferSize_bytes),
                "<outBufferSize_bytes>" : str(self.outBufferSize_bytes),
                "<saltBufferSize_bytes>" : str(self.saltBufferSize_bytes),
                "<ctBufferSize_bytes>" : str(self.ctBufferSize_bytes),
                "<word_size>" : str(self.wordSize)
        }

        rep = dict((re.escape(k), v) for k, v in rep.items())
        pattern = re.compile("|".join(rep.keys()))
        self.code = pattern.sub(lambda m: rep[re.escape(m.group(0))], template)

    def specifyMD5(self, max_in_bytes=128, max_salt_bytes=32, dklen=0, max_ct_bytes=0):
        self.specify_hash_sizes(512, 128)
        max_num_blocks = 3
        self.wordSize = 4
        self.set_buffer_sizes_for_hashing(max_num_blocks)
        max_out_bytes = self.hashDigestSize_bits // 8
        if dklen != 0:
            # Adjust output size to be a multiple of the digest
            max_out_bytes = ceil_to_mult(dklen, (self.hashDigestSize_bits // 8))
        self.set_max_buffer_sizes(max_in_bytes, max_out_bytes, max_salt_bytes, max_ct_bytes)
        self.fill_template()
        return max_out_bytes

    def specifySHA1(self, max_in_bytes=128, max_salt_bytes=32, dklen=0, max_ct_bytes=0):
        self.specify_hash_sizes(512, 160)
        max_num_blocks = 3
        self.wordSize = 4
        self.set_buffer_sizes_for_hashing(max_num_blocks)
        max_out_bytes = self.hashDigestSize_bits // 8
        if dklen != 0:
            # Adjust output size to be a multiple of the digest
            max_out_bytes = ceil_to_mult(dklen, (self.hashDigestSize_bits // 8))
        self.set_max_buffer_sizes(max_in_bytes, max_out_bytes, max_salt_bytes, max_ct_bytes)
        self.fill_template()
        return max_out_bytes

    def specifySHA2(self, hash_digest_size_bits=256, max_in_bytes=128, max_salt_bytes=32, dklen=0, max_ct_bytes=0):
        assert hash_digest_size_bits in [224, 256, 384, 512]
        hash_block_size_bits = 512
        if hash_digest_size_bits >= 384:
            hash_block_size_bits = 1024
        self.specify_hash_sizes(hash_block_size_bits, hash_digest_size_bits)
        if hash_digest_size_bits == 512:
            max_num_blocks = 2
            self.wordSize = 8
        else:
            max_num_blocks = 3
            self.wordSize = 4
        self.set_buffer_sizes_for_hashing(max_num_blocks)
        max_out_bytes = self.hashDigestSize_bits // 8
        if dklen != 0:
            # Adjust output size to be a multiple of the digest
            max_out_bytes = ceil_to_mult(dklen, (self.hashDigestSize_bits // 8))

        self.set_max_buffer_sizes(max_in_bytes, max_out_bytes, max_salt_bytes, max_ct_bytes)
        self.fill_template()
        return max_out_bytes
