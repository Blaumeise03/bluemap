
cdef class StreamReader:
    cdef object file
    cdef object path
    cdef int compressed
    cdef object decompressor
    cdef bytearray buffer

    cdef enable_compression(self)
    cdef start_decompression(self)
    cdef bytes read(self, int size)

cdef class StreamWriter:
    cdef object file
    cdef object path
    cdef int compressed
    cdef object compressor
    cdef bytearray buffer

    cdef c_write(self, bytes data)
    cdef flush_buffer(self)
