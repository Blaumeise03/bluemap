import os
import zlib
from pathlib import Path

cdef class StreamReader:
    """
    A simple class to read from a file, optionally decompressing it.

    Compatible to the Java DeflaterOutputStream and InflaterInputStream.
    """

    def __init__(self, path: Path | os.PathLike[str] | str, compressed=False):
        self.file = None
        self.path = path
        self.compressed = compressed
        self.decompressor = None
        self.buffer = bytearray()

    def __enter__(self):
        if not isinstance(self.path, Path):
            self.path = Path(self.path)
        self.file = self.path.open('rb')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.compressed:
            self.decompressor.flush()
        self.file.close()
        self.file = None

    cdef enable_compression(self):
        self.compressed = True

    cdef start_decompression(self):
        if not self.compressed:
            return
        self.decompressor = zlib.decompressobj()

    cdef bytes read(self, int size):
        if self.compressed:
            while len(self.buffer) < size:
                chunk = self.file.read(1024)
                if not chunk:
                    break
                self.buffer.extend(self.decompressor.decompress(chunk))
            ret = bytes(self.buffer[:size])
            self.buffer[:size] = b''
        else:
            ret = self.file.read(size)
        return ret


cdef class StreamWriter:
    """
    A simple class to write to a file, optionally compressing it.

    Compatible to the Java DeflaterOutputStream and InflaterInputStream.
    """

    def __init__(self, path: Path | os.PathLike[str] | str, compressed=False):
        self.file = None
        self.path = path
        self.compressed = compressed
        self.compressor = None
        self.buffer = bytearray()

    def __enter__(self):
        if not isinstance(self.path, Path):
            self.path = Path(self.path)
        self.file = self.path.open('wb')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()
        self.file.close()
        self.file = None

    def enable_compression(self):
        """
        Enable compression for this stream, requires a call to start_compression before writing
        :return:
        """
        self.compressed = True

    def start_compression(self):
        """
        Start the compression process if compression is enabled
        :return:
        """
        if not self.compressed:
            return
        self.compressor = zlib.compressobj()

    cdef c_write(self, data: bytes):
        if self.compressed and self.compressor:
            self.buffer.extend(self.compressor.compress(data))
        else:
            self.buffer.extend(data)

    def write(self, data: bytes) :
        self.c_write(data)
        if len(self.buffer) > 1024:
            self.flush_buffer()

    cdef flush_buffer(self):
        if self.buffer:
            self.file.write(self.buffer)
            self.buffer[:] = b''

    def flush(self):
        if self.compressed and self.compressor:
            self.buffer.extend(self.compressor.flush())
        self.flush_buffer()
