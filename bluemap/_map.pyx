# distutils: language = c++
import os
import weakref
import zlib
from pathlib import Path
from typing import Generator

from libc.stdlib cimport free, malloc
from libcpp cimport bool as cbool
from libcpp.string cimport string
from libcpp.vector cimport vector

from .stream import StreamReader, StreamWriter
from .stream cimport StreamReader, StreamWriter

cdef extern from "stdint.h":
    ctypedef unsigned char uint8_t

cdef extern from "Image.h":
    cdef struct Color:
        uint8_t red
        uint8_t green
        uint8_t blue
        uint8_t alpha

cdef extern from "Map.h" namespace "bluemap":
    ctypedef unsigned long long id_t

    # All listed methods are thread-safe and memory safe. All operations that will modify or retrieve data from the map
    # will be blocked as long as any worker is rendering.
    # noinspection PyPep8Naming,PyUnresolvedReferences
    cdef cppclass CMap "bluemap::Map":
        struct CMapOwnerLabel "MapOwnerLabel":
            id_t owner_id
            unsigned long long x
            unsigned long long y
            size_t count

            CMapOwnerLabel()
            CMapOwnerLabel(id_t owner_id)

        # noinspection PyPep8Naming
        cppclass CColumnWorker "ColumnWorker":
            CColumnWorker(CMap *map, unsigned int start_x, unsigned int end_x) except +
            # This method is thread-safe and can be called from multiple threads simultaneously on different objects
            # to speed up rendering. Calling this method on the same object from multiple threads is not possible and
            # will result in the two calls being serialized.
            void render() except + nogil

        Map() except +

        CMap.CColumnWorker * create_worker(unsigned int start_x, unsigned int end_x) except +

        void render_multithreaded() except +
        void calculate_influence() except +
        void load_data(const string& filename) except +
        void load_data(const vector[COwnerData]& owners,
                       const vector[CSolarSystemData]& solar_systems,
                       const vector[CJumpData]& jumps) except +
        void update_size(unsigned int width, unsigned int height, unsigned int sample_rate) except +
        void save(const string& path) except +

        vector[CMap.CMapOwnerLabel] calculate_labels() except +

        # All three functions will transfer the ownership of the ptr
        uint8_t *retrieve_image() except +
        id_t *create_owner_image() except +
        # Will raise exception if size does not match (ptr will still be deallocated)
        void set_old_owner_image(id_t *old_owner_image, unsigned int width, unsigned int height) except +

        unsigned int get_width()
        unsigned int get_height()
        cbool has_old_owner_image()

    cdef struct COwnerData "bluemap::OwnerData":
        id_t id
        Color color
        bint npc

    cdef struct CSolarSystemData "bluemap::SolarSystemData":
        id_t id
        id_t constellation_id
        id_t region_id
        unsigned int x
        unsigned int y
        bint has_station
        double sov_power
        id_t owner

    cdef struct CJumpData "bluemap::JumpData":
        id_t sys_from
        id_t sys_to


cdef class BufferWrapper:
    cdef void * data_ptr
    cdef Py_ssize_t width
    cdef Py_ssize_t height
    cdef Py_ssize_t channels
    cdef Py_ssize_t itemsize
    # 1 = uint8_t, 2 = id_t
    cdef int dtype

    cdef Py_ssize_t shape[3]
    cdef Py_ssize_t strides[3]

    def __cinit__(self):
        self.data_ptr = NULL
        self.width = 0
        self.height = 0
        self.channels = 0
        self.itemsize = 1

    # noinspection PyAttributeOutsideInit
    cdef set_data(
            self,
            int width, int height, void * data_ptr,
            int channels, int dtype=1):
        self.data_ptr = data_ptr
        self.width = width
        self.height = height
        self.channels = channels
        self.dtype = dtype
        if dtype == 1:
            self.itemsize = 1
        elif dtype == 2:
            self.itemsize = 8
        else:
            self.itemsize = 1

        self.shape[0] = self.height
        self.shape[1] = self.width
        self.shape[2] = self.channels
        self.strides[0] = self.width * self.channels * self.itemsize
        self.strides[1] = self.channels * self.itemsize
        self.strides[2] = self.itemsize

    def __dealloc__(self):
        free(self.data_ptr)
        self.data_ptr = NULL

    def __getbuffer__(self, Py_buffer *buffer, int flags):
        buffer.buf = <char *> self.data_ptr
        if self.dtype == 1:
            buffer.format = 'B'
        elif self.dtype == 2:
            buffer.format = 'Q'
        else:
            buffer.format = 'c'
        buffer.internal = NULL
        buffer.itemsize = self.itemsize
        buffer.len = self.width * self.height * self.channels * self.itemsize
        buffer.ndim = 3
        buffer.obj = self
        buffer.readonly = 0
        buffer.shape = self.shape
        buffer.strides = self.strides
        buffer.suboffsets = NULL

    def as_ndarray(self):
        # noinspection PyPackageRequirements
        import numpy as np
        return np.array(self, copy=False)

    def as_pil_image(self):
        # noinspection PyPackageRequirements
        import PIL.Image
        # noinspection PyTypeChecker
        return PIL.Image.frombuffer(
            'RGBA'
            '', (self.width, self.height),
            self, 'raw', 'RGBA', 0, 1)

    @property
    def size(self):
        return self.width, self.height

    cdef object get_value(self, int x, int y, int c):
        if self.dtype == 1:
            return (<uint8_t *> self.data_ptr)[x * self.strides[1] + y * self.strides[0] + c * self.strides[2]]
        elif self.dtype == 2:
            return (
                <id_t *> (<char *> self.data_ptr + x * self.strides[1] + y * self.strides[0] + c * self.strides[2])
            )[0]
        else:
            return (<char *> self.data_ptr)[x * self.strides[1] + y * self.strides[0] + c * self.strides[2]]

    cdef set_value(self, int x, int y, int c, object value):
        cdef uint8_t val_ui8
        cdef id_t val_id
        cdef char val_char
        if self.dtype == 1:
            val_ui8 = value
            (<uint8_t *> self.data_ptr)[x * self.strides[1] + y * self.strides[0] + c * self.strides[2]] = val_ui8
        elif self.dtype == 2:
            if value < 0:
                val_id = 0
            else:
                val_id = value
            (
                <id_t *> (<char *> self.data_ptr + x * self.strides[1] + y * self.strides[0] + c * self.strides[2])
            )[0] = val_id
        else:
            val_char = value
            (<char *> self.data_ptr)[x * self.strides[1] + y * self.strides[0] + c * self.strides[2]] = val_char

    # noinspection DuplicatedCode
    def __getitem__(self, index: tuple[int, int] | tuple[int, int, int]) -> int | tuple[int, ...]:
        if not isinstance(index, tuple) or len(index) < 2 or len(index) > 3:
            raise TypeError("Invalid index type, must be a tuple of length 2 or 3")
        x, y = index[:2]
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            raise IndexError("Index out of range, x and y must be in the range of the image")
        if len(index) == 2:
            if self.channels == 1:
                return self.get_value(x, y, 0)
            return tuple(self.get_value(x, y, c) for c in range(self.channels))
        c = index[2]
        if c < 0 or c >= self.channels:
            raise IndexError("Index out of range, c must be in the range of the image channels")
        return self.get_value(x, y, c)

    # noinspection DuplicatedCode
    def __setitem__(self, index: tuple[int, int] | tuple[int, int, int], value: int | tuple[int, ...]) -> None:
        if not isinstance(index, tuple) or len(index) < 2 or len(index) > 3:
            raise TypeError("Invalid index type, must be a tuple of length 2 or 3")
        x, y = index[:2]
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            raise IndexError("Index out of range, x and y must be in the range of the image")
        if len(index) == 2:
            if self.channels == 1 and not isinstance(value, tuple):
                self.set_value(x, y, 0, value)
                return
            for c in range(self.channels):
                self.set_value(x, y, c, value[c])
            return
        c = index[2]
        if c < 0 or c >= self.channels:
            raise IndexError("Index out of range, c must be in the range of the image channels")
        self.set_value(x, y, c, value)

    def __iter__(self) -> Generator[tuple[int, ...], None]:
        for y in range(self.height):
            for x in range(self.width):
                yield self[x, y]

    def __len__(self) -> int:
        return self.width * self.height * self.channels

cdef class ColumnWorker:
    cdef CMap.CColumnWorker * c_worker
    cdef object _map

    def __cinit__(self, SovMap map_, unsigned int start_x, unsigned int end_x):
        if not map:
            raise ValueError("Map is not initialized")
        self.c_worker = map_.c_map.create_worker(start_x, end_x)
        self._map = weakref.ref(map_)
        map_.add_worker(self)

    def __dealloc__(self):
        cdef SovMap map_ = self._map()
        if map_ is not None:
            map_.remove_worker(self)
        del self.c_worker

    cdef free(self):
        del self.c_worker
        self.c_worker = NULL

    def render(self) -> None:
        """
        Renders this column (blocking). Rendering happens without the GIL, so this method can be called on different
        objects from multiple threads simultaneously to speed up rendering. Calling this method on the same object
        from multiple threads is not possible and will result in the two calls being serialized.

        See also SovMap.render() for an example multithreaded rendering implementation. It is recommended to use
        that method instead of calling this method directly.
        :return:
        """
        # Retrieve a real reference to the map to prevent premature deallocation
        cdef object map_ = self._map()
        if not map_:
            raise ReferenceError("The sov map corresponding to this worker has been deallocated")
        if not self.c_worker:
            raise ReferenceError("The sov map corresponding to this worker has been deallocated (the worker is freed)")
        with nogil:
            # Call the C++ render method, thread-safety is ensured by the C++ code
            self.c_worker.render()

cdef class SolarSystem:
    cdef CSolarSystemData _c_data

    def __init__(self, id_: int, constellation_id: int, region_id: int, x: int, y: int, has_station: bool,
                 sov_power: float, owner: int | None):
        if type(x) is not int or type(y) is not int:
            raise TypeError("x and y must be ints")
        if owner is None:
            owner = 0
        if type(owner) is not int:
            raise TypeError("owner must be an int")
        if type(id_) is not int or type(constellation_id) is not int or type(region_id) is not int:
            raise TypeError("id, constellation_id and region_id must be ints")
        if type(has_station) is not bool:
            raise TypeError("has_station must be a bool")
        self._c_data = CSolarSystemData(
            id=id_, constellation_id=constellation_id, region_id=region_id, x=x, y=y,
            has_station=has_station, sov_power=sov_power, owner=owner)

    @property
    def c_data(self):
        return self._c_data

    @property
    def id(self):
        return self._c_data.id

    @property
    def constellation_id(self):
        return self._c_data.constellation_id

    @property
    def region_id(self):
        return self._c_data.region_id

    @property
    def x(self):
        return self._c_data.x

    @property
    def y(self):
        return self._c_data.y

    @property
    def has_station(self):
        return self._c_data.has_station

    @property
    def sov_power(self):
        return self._c_data.sov_power

    @property
    def owner(self):
        return self._c_data.owner

cdef class Owner:
    cdef COwnerData _c_data

    def __init__(self, id_: int, color: tuple[int, int, int] | tuple[int, int, int, int], npc: bool):
        if type(id_) is not int:
            raise TypeError("id must be an int")
        if type(npc) is not bool:
            raise TypeError("npc must be a bool")
        if len(color) < 3 or len(color) > 4:
            raise ValueError("color must be a tuple of 3 or 4 ints")
        self._c_data = COwnerData(
            id=id_, color=Color(
                red=color[0], green=color[1], blue=color[2],
                alpha=color[3] if len(color) > 3 else 255
            ), npc=npc)

    @property
    def c_data(self):
        return self._c_data

    @property
    def id(self):
        return self._c_data.id

    @property
    def color(self):
        return self._c_data.color

    @property
    def npc(self):
        return self._c_data.npc

cdef class MapOwnerLabel:
    cdef CMap.CMapOwnerLabel _c_data

    def __init__(self, owner_id: int = None, x: int = None, y: int = None, count: int = None):
        if owner_id is None and x is None and y is None and count is None:
            return
        self._c_data.owner_id = owner_id or 0
        self._c_data.x = x or 0
        self._c_data.y = y or 0
        self._c_data.count = count or 0

    def __cinit__(self):
        self._c_data = CMap.CMapOwnerLabel()

    @staticmethod
    cdef MapOwnerLabel from_c_data(CMap.CMapOwnerLabel c_data):
        cdef MapOwnerLabel obj = MapOwnerLabel()
        obj._c_data = c_data
        return obj

    @property
    def owner_id(self):
        return self._c_data.owner_id

    @property
    def x(self):
        return self._c_data.x

    @property
    def y(self):
        return self._c_data.y

    @property
    def count(self):
        return self._c_data.count

cdef class OwnerImage:
    cdef BufferWrapper _buffer

    def __init__(self, buffer: BufferWrapper):
        self._buffer = buffer

    def as_ndarray(self):
        return self._buffer.as_ndarray()

    def __getitem__(self, index: tuple[int, int]) -> int | None:
        val = self._buffer[index]
        if val == 0:
            return None
        return val

    def __setitem__(self, index: tuple[int, int], value: int | None) -> None:
        if value is None:
            value = 0
        self._buffer[index] = value

    def __len__(self):
        return len(self._buffer)

    def save(self, path: Path | os.PathLike[str] | str, compressed=True) -> None:
        import struct
        if not isinstance(path, Path):
            path = Path(path)
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        cdef StreamWriter stream
        with StreamWriter(path, compressed=compressed) as stream:
            if compressed:
                stream.c_write(b'SOVCV1.0')
            else:
                stream.c_write(b'SOVNV1.0')
            stream.start_compression()
            stream.c_write(struct.pack(">II", self._buffer.width, self._buffer.height))
            for x in range(self._buffer.width):
                for y in range(self._buffer.height):
                    val = self._buffer[x, y]
                    if val == 0:
                        val = -1
                    stream.c_write(struct.pack(">q", val))

    @staticmethod
    cdef BufferWrapper _load_from_file(path: Path):
        import struct
        cdef BufferWrapper buffer = BufferWrapper()  # type: BufferWrapper
        cdef void * data_ptr = NULL
        cdef StreamReader stream = StreamReader(path, compressed=False)
        with stream:
            header = stream.read(8)
            if header not in (b'SOVCV1.0', b'SOVNV1.0'):
                raise ValueError("Invalid file header")
            compressed = header == b'SOVCV1.0'
            in_stream = None
            if compressed:
                stream.enable_compression()
            stream.start_decompression()
            # Read width and height as int
            width, height = struct.unpack(">II", stream.read(8))
            if width <= 0 or height <= 0:
                raise ValueError("Invalid image size")
            # Create buffer
            data_ptr = malloc(width * height * sizeof(id_t))
            if data_ptr is NULL:
                raise MemoryError("Failed to allocate memory")
            buffer.set_data(width, height, data_ptr, 1, 2)
            # Read data
            for x in range(width):
                for y in range(height):
                    buffer[x, y] = struct.unpack(">q", stream.read(8))[0]
        return buffer

    @classmethod
    def load_from_file(cls, path: Path | os.PathLike[str] | str) -> OwnerImage:
        if not isinstance(path, Path):
            path = Path(path)
        if not path.exists():
            raise FileNotFoundError("File not found")
        buffer = OwnerImage._load_from_file(path)
        # noinspection PyTypeChecker
        return OwnerImage(buffer)

cdef class SovMap:
    # Ok, so these two attributes are important and need to be handled very carefully to avoid memory leaks or
    # segfaults. The way it works: On the C++ code, every worker has a reference to the map. However, only the map is
    # responsible for managing memory. So we need to be carefull when deleting the map, while workers are still alive.
    # There are two safeguards in place to avoid this:
    # 1. The map has a global shared mutex, every worker will lock this mutex while rendering, this will prevent the map
    #    from being deallocated while a worker is rendering. This will also block all operations on the map that will
    #    modify or retrieve data from the map.
    # 2. On the python side, the map has a list of workers, and every worker holds a weak reference to the map. When the
    #    render method is called, the worker will retrieve a strong reference to the map, and will keep it until the
    #    rendering is done. This will prevent the map from being deallocated while a worker is rendering in the first
    #    place.
    # Going further, all function that are exposed to the python side are thread-safe and memory safe and can be called
    # without any restrictions. All cdef functions need to be handled with care and are not supposed to be used.
    cdef CMap * c_map
    cdef object workers  # type: list[CMap.CColumnWorker]

    cdef object __weakref__

    cdef int _calculated

    # This data is only a copy of the data in the C++ map, it is used for other operations like rendering labels
    # which only happen on the python side. This data is passed initially to the C++ map for rendering
    cdef long long _width
    cdef long long _height
    cdef long long _offset_x
    cdef long long _offset_y
    cdef int _sample_rate
    cdef double _scale
    _owners: dict[int, Owner]
    _systems: dict[int, SolarSystem]
    _connections: list[tuple[int, int]]

    def __init__(
            self,
            width: int = 928 * 2, height: int = 1024 * 2,
            offset_x: int = 208, offset_y: int = 0
    ):
        self._width = width
        self._height = height
        self._offset_x = offset_x
        self._offset_y = offset_y
        self._sample_rate = 8
        self._scale = 4.8445284569785E17 / ((self.width - 20) / 2.0)
        self._owners = {}
        self._systems = {}
        self._connections = []

    ### Internal Methods - handle with care! ###

    def __cinit__(self):
        self.c_map = new CMap()
        self._calculated = False
        self.workers = []

    def __dealloc__(self):
        cdef ColumnWorker worker
        for worker in self.workers:
            self.remove_worker(worker)
            worker.free()
            del worker
        del self.c_map

    cdef void _sync_data(self):
        self.c_map.update_size(
            <unsigned int> self._width,
            <unsigned int> self._height,
            <unsigned int> self._sample_rate,
        )

    cdef void remove_worker(self, worker):
        self.workers.remove(worker)

    cdef void add_worker(self, worker):
        self.workers.append(worker)

    ### Public Interface (more or less) ###

    def load_data_from_file(self, filename: str):
        # noinspection PyTypeChecker
        self.c_map.load_data(filename.encode('utf-8'))

    def calculate_influence(self):
        self.c_map.calculate_influence()
        self._calculated = True

    def create_workers(self, count: int):
        cdef unsigned int width = self.c_map.get_width()
        cdef unsigned int start_x, end_x
        workers = []
        cdef int i

        for i in range(count):
            start_x = i * width // count
            end_x = (i + 1) * width // count
            workers.append(ColumnWorker(self, start_x, end_x))
        return workers

    def save(self, path: str):
        # noinspection PyTypeChecker
        self.c_map.save(path.encode('utf-8'))

    def load_data(self, owners: list, systems: list, connections: list):
        """
        Load data into the map. Only systems inside the map will be saved, other systems will be ignored.

        :param owners: a list of owner data, each entry is a dict with the keys 'id' (int), 'color' (3-tuple) and 'npc' (bool)
        :param systems: a list of system data, each entry is a dict with the keys 'id', 'x', 'z', 'constellation_id', 'region_id', 'has_station', 'sov_power' and 'owner'
        :param connections: a list of jump data, each entry is a tuple of two system IDs
        :return:
        """
        cdef vector[COwnerData] owner_data
        cdef vector[CSolarSystemData] system_data
        cdef vector[CJumpData] jump_data
        self._connections.clear()
        self._systems.clear()
        self._owners.clear()

        cdef object owner_obj
        for owner in owners:
            owner_obj = Owner(
                id_=owner['id'],
                color=owner['color'],
                npc=owner['npc'])
            self._owners[owner_obj.id] = owner_obj
            # noinspection PyUnresolvedReferences
            owner_data.push_back(owner_obj.c_data)

        cdef double x, y, z, width, height, offset_x, offset_y, scale
        offset_x = self._offset_x
        offset_y = self._offset_y
        scale = self._scale
        width = self._width
        height = self._height
        cdef object skipped = set()
        cdef object system_obj
        for system in systems:
            if system['x'] is None or system['z'] is None:
                skipped.add(system['id'])
                continue
            x = system['x']
            z = system['z']
            x = ((x / scale) + width / 2 + offset_x) + 0.5
            z = ((z / scale) + height / 2 + offset_y) + 0.5
            if x < 0 or x >= width or z < 0 or z >= height:
                skipped.add(system['id'])
                continue
            system_obj = SolarSystem(
                id_=system['id'],
                constellation_id=system['constellation_id'],
                region_id=system['region_id'],
                x=int(x), y=int(z),
                has_station=system['has_station'],
                sov_power=system['sov_power'],
                owner=system['owner'])
            self._systems[system_obj.id] = system_obj
            # noinspection PyUnresolvedReferences
            system_data.push_back(system_obj.c_data)

        for connection in connections:
            if connection[0] in skipped or connection[1] in skipped:
                continue
            # noinspection PyUnresolvedReferences
            jump_data.push_back(CJumpData(sys_from=connection[0], sys_to=connection[1]))
            self._connections.append(connection)

        self.c_map.load_data(owner_data, system_data, jump_data)
        print("Skipped %d systems" % len(skipped))

    def render(self, thread_count: int = 1) -> None:
        """
        Render the map. This method will calculate the influence of each owner and render the map. The rendering is done
        in parallel using the given number of threads.

        Warning: Calling this method while a rendering is already in progress is not safe and is considered undefined
        behavior.
        :param thread_count:
        :return:
        """
        if not self._calculated:
            self.calculate_influence()
        from concurrent.futures.thread import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=thread_count) as pool:
            # If you want to implement your own rendering, be carefull with the ColumnWorker class. It's not meant to be
            # used on its own. It does only hold a weak reference to its map object - if the map object goes out of
            # scope and gets garbage collected, the ColumnWorker will not work anymore. Disconnected workers might raise
            # an exception, but this is not guaranteed.
            #
            # DEALLOCATION OF THE MAP OBJECT WHILE A RENDERING IS IN PROGRESS IS NOT SAFE AND WILL SEGFAULT! So make
            # sure to always hold a reference to the map before creating workers.
            #
            # Additionally, the ColumnWorker is only partially thread safe. While it *should* be okay-ish, creating
            # multiple workers for the same column is not recommended as not all operations are secured by locks
            # because they are not needed for the rendering process with disjunct workers. You can create custom
            # workers, but it is recommended to use create_workers once per map. Also, between creation of the workers
            # and the rendering, the map should not be modified, as the workers won't be updated (i.e. size).
            workers = self.create_workers(thread_count)
            pool.map(ColumnWorker.render, workers)

    def calculate_labels(self) -> list[MapOwnerLabel]:
        cdef vector[CMap.CMapOwnerLabel] labels = self.c_map.calculate_labels()
        # noinspection PyTypeChecker
        return [MapOwnerLabel.from_c_data(label) for label in labels]

    cdef _retrieve_image_buffer(self):
        cdef uint8_t * data = self.c_map.retrieve_image()
        if data == NULL:
            return None
        width = self.c_map.get_width()
        height = self.c_map.get_height()
        image_base = BufferWrapper()
        image_base.set_data(width, height, data, 4, 1)
        return image_base

    cdef _retrieve_owner_buffer(self):
        cdef id_t * data = self.c_map.create_owner_image()
        if data == NULL:
            return None
        width = self.c_map.get_width()
        height = self.c_map.get_height()
        image_base = BufferWrapper()
        image_base.set_data(width, height, data, 1, 2)
        return image_base

    def get_image(self) -> BufferWrapper | None:
        """
        Get the image as a buffer. This method will remove the image from the map, further calls to this method will
        return None. The buffer wrapper provides already two methods to convert the image to a Pillow image or a numpy
        array. But it can be used by any function that supports the buffer protocol.

        See https://docs.python.org/3/c-api/buffer.html

        >>> import PIL.Image
        >>> sov_map = SovMap()
        >>> #...
        >>> image = sov_map.get_image().as_pil_image()

        Or to create a numpy array:

        >>> image = sov_map.get_image().as_ndarray()

        :return: the image buffer if available, None otherwise
        """
        return self._retrieve_image_buffer()

    def save(self, path: Path | os.PathLike[str] | str) -> None:
        """
        Save the image to a file. Requires Pillow or OpenCV to be installed. Use the get_image method if you want to
        get better control over the image.

        This method will remove the image from the map, further calls to get_image will return None and further calls
        to save will raise a ValueError.

        :param path:
        :return:
        """
        if not isinstance(path, Path):
            path = Path(path)
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        strategy = None
        try:
            import PIL
            strategy = "PIL"
        except ImportError:
            try:
                import cv2
                strategy = "cv2"
            except ImportError:
                pass
        if strategy is None:
            raise ImportError(
                "Please install Pillow (pip install Pillow) or OpenCV (pip install opencv-python) to save images.")
        if strategy == "PIL":
            image = self.get_image().as_pil_image()
            if image is None:
                raise ValueError("No image available")
            image.save(path)
        elif strategy == "cv2":
            import cv2
            image = self.get_image().as_ndarray()
            if image is None:
                raise ValueError("No image available")
            cv2.imwrite(str(path), image)

    def get_owner_map(self):
        return self._retrieve_owner_buffer()

    def update_size(self, width: int | None = None, height: int | None = None, sample_rate: int | None = None) -> None:
        """
        Update the size of the map. This will recalculate the scale automatically.
        :param width: the new width (or None to keep the current width)
        :param height: the new height (or None to keep the current height)
        :param sample_rate: the new sample rate (or None to keep the current sample rate)
        :return:
        """
        if width is not None:
            self._width = width
        if height is not None:
            self._height = height
        if sample_rate is not None:
            self._sample_rate = sample_rate
        self._sample_rate = sample_rate
        self._scale = 4.8445284569785E17 / ((self.width - 20) / 2.0)
        self._sync_data()

    @property
    def calculated(self):
        return self._calculated

    @property
    def systems(self) -> dict[int, SolarSystem]:
        """
        Get a dictionary of all solar systems in the map. The key is the system ID, the value is the SolarSystem object.

        Modifications to the dict or the SolarSystem objects will not be reflected in the map. Modifications might
        cause unexpected behavior.
        :return:
        """
        return self._systems

    @property
    def owners(self) -> dict[int, Owner]:
        """
        Get a dictionary of all owners in the map. The key is the owner ID, the value is the Owner object.

        Modifications to the dict or the Owner objects will not be reflected in the map. Modifications might cause
        unexpected behavior.
        :return:
        """
        return self._owners

    @property
    def connections(self) -> list[tuple[int, int]]:
        """
        Get a list of all connections in the map. Each connection is a tuple of two system IDs.

        Modifications to the list will not be reflected in the map. Modifications might cause unexpected behavior.
        :return:
        """
        return self._connections

    @property
    def width(self) -> int:
        """
        The width of the map in pixels.
        :return:
        """
        return self._width

    @width.setter
    def width(self, value: int):
        self.update_size(width=value)

    @property
    def height(self) -> int:
        """
        The height of the map in pixels.
        :return:
        """
        return self._height

    @height.setter
    def height(self, value: int):
        self.update_size(height=value)

    @property
    def resolution(self) -> tuple[int, int]:
        """
        The resolution of the map in pixels.
        :return:
        """
        return self._width, self._height

    @resolution.setter
    def resolution(self, value: tuple[int, int]):
        self.update_size(width=value[0], height=value[1])

    @property
    def offset_x(self) -> int:
        return self._offset_x

    @property
    def offset_y(self) -> int:
        return self._offset_y

    @property
    def sample_rate(self) -> int:
        """
        The sample rate used to calculate the position of owner labels. Default is 8.
        :return: the sample rate
        """
        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, value: int):
        self.update_size(sample_rate=value)

    @property
    def scale(self) -> float:
        """
        The scale used to calculate the position of solar systems. Default is 4.8445284569785E17 / ((width - 20) / 2.0).
        If other values are set, the scale will be recalculated. So if you want to set a custom scale, set scale after
        setting width and height.
        :return:
        """
        return self._scale

    @scale.setter
    def scale(self, value: float):
        self._scale = value
