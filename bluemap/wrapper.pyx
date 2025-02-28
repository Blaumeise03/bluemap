# distutils: language = c++
import weakref

from libc.stdlib cimport free
from libcpp.string cimport string
from libcpp.vector cimport vector

#import numpy as np
#cimport numpy as np
#np.import_array()

from cython.parallel import prange

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

    cdef cppclass CMap "bluemap::Map":
        cppclass CColumnWorker "ColumnWorker":
            CColumnWorker(CMap *map, unsigned int start_x, unsigned int end_x) except +
            void render() except + nogil

        Map() except +
        # unsigned int width
        # unsigned int height
        # unsigned int offset_x
        # unsigned int offset_y
        # double scale
        # double power_falloff

        CMap.CColumnWorker * create_worker(unsigned int start_x, unsigned int end_x)

        void render_multithreaded() except +
        void calculate_influence() except +
        void load_data(const string& filename) except +
        void load_data(const vector[OwnerData]& owners,
                       const vector[SolarSystemData]& solar_systems,
                       const vector[JumpData]& jumps) except +
        void save(const string& path) except +

        uint8_t *retrieve_image() except +
        id_t *create_owner_image() except +

        unsigned int get_width()
        unsigned int get_height()

    cdef struct OwnerData:
        id_t id
        Color color
        bint npc

    cdef struct SolarSystemData:
        id_t id
        id_t constellation_id
        id_t region_id
        unsigned int x
        unsigned int y
        bint has_station
        double sov_power
        id_t owner

    cdef struct JumpData:
        id_t sys_from
        id_t sys_to


cdef class ImageWrapper:
    cdef void* data_ptr
    cdef Py_ssize_t width
    cdef Py_ssize_t height
    cdef Py_ssize_t channels

    cdef Py_ssize_t shape[3]
    cdef Py_ssize_t strides[3]

    def __cinit__(self):
        self.data_ptr = NULL
        self.width = 0
        self.height = 0
        self.channels = 4

    cdef set_data(self, int width, int height, void* data_ptr):
        self.data_ptr = data_ptr
        self.width = width
        self.height = height
        #print("Created buffer")

    def __dealloc__(self):
        free(self.data_ptr)
        self.data_ptr = NULL
        #print("Deallocated buffer")

    #def __array__(self):
    #    #cdef np.npy_intp shape[1]
    #    #shape[0] = <np.npy_int> self.width * self.height
    #    ##shape[1] = <np.npy_int> self.height
    #    #ndarray = np.PyArray_SimpleNewFromData(1, shape, np.uint8, self.data_ptr)
    #    cdef np.uint8_t[::1] arr = <np.uint8_t [:self.height * self.width]>self.data_ptr
    #    return arr
    def __getbuffer__(self, Py_buffer *buffer, int flags):
        cdef Py_ssize_t itemsize = 1

        self.shape[0] = self.height
        self.shape[1] = self.width
        self.shape[2] = self.channels
        self.strides[0] = self.width * self.channels
        self.strides[1] = self.channels
        self.strides[2] = 1
        buffer.buf = <char *> self.data_ptr
        buffer.format = 'B'
        buffer.internal = NULL
        buffer.itemsize = itemsize
        buffer.len = self.width * self.height * self.channels * itemsize
        buffer.ndim = 3
        buffer.obj = self
        buffer.readonly = 0
        buffer.shape = self.shape
        buffer.strides = self.strides
        buffer.suboffsets = NULL
        #print("Returned buffer with shape ", self.shape, " and strides ", self.strides)


cdef class ColumnWorker:
    cdef CMap.CColumnWorker * c_worker
    cdef object _map

    def __cinit__(self, Map map_, unsigned int start_x, unsigned int end_x):
        if not map:
            raise ValueError("Map is not initialized")
        self.c_worker = map_.c_map.create_worker(start_x, end_x)
        self._map = weakref.proxy(map_)
        self._map._add_worker(self)
        #print("Allocated worker")

    def __dealloc__(self):
        try:
            self._map._remove_worker(self)
        except ReferenceError:
            pass
        del self.c_worker
        #print("Deallocated worker")

    def _free(self):
        del self.c_worker
        self.c_worker = NULL

    def render(self) -> None:
        if not self.c_worker:
            raise ReferenceError("The sov map corresponding to this worker has been deallocated")
        with nogil:
            self.c_worker.render()

cdef class Map:
    cdef CMap * c_map
    cdef int _calculated
    cdef object workers

    cdef object __weakref__

    def __init__(self):
        pass

    def __cinit__(self):
        self.c_map = new CMap()
        self._calculated = False
        self.workers = []
        print("Allocated map")

    def __dealloc__(self):
        for worker in self.workers:
            self._remove_worker(worker)
            worker._free()
            del worker
        del self.c_map
        print("Deallocated map")

    def _remove_worker(self, worker):
        self.workers.remove(worker)

    def _add_worker(self, worker):
        self.workers.append(worker)

    def load_data_from_file(self, filename: str):
        # noinspection PyTypeChecker
        self.c_map.load_data(filename.encode('utf-8'))

    def calculate_influence(self):
        self.c_map.calculate_influence()
        self._calculated = True

    @property
    def calculated(self):
        return self._calculated

    def render(self, thread_count: int = 1):
        if not self._calculated:
            self.calculate_influence()
        cdef unsigned int width = self.c_map.get_width()
        cdef unsigned int height = self.c_map.get_height()
        cdef unsigned int start_x, end_x
        cdef vector[CMap.CColumnWorker *] workers
        cdef int j
        cdef int n = thread_count
        cdef int sum = 0

        try:
            for i in range(thread_count):
                start_x = i * width // thread_count
                end_x = (i + 1) * width // thread_count
                workers.push_back(self.c_map.create_worker(start_x, end_x))
            for j in prange(n, nogil=True):
                workers[j].render()
        finally:
            for worker in workers:
                del worker

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
        cdef vector[OwnerData] owner_data
        cdef vector[SolarSystemData] system_data
        cdef vector[JumpData] jump_data

        for owner in owners:
            owner_data.push_back(OwnerData(
                id=owner['id'],
                color=Color(red=owner['color'][0],
                            green=owner['color'][1],
                            blue=owner['color'][2], alpha=owner['color'][3]),
                npc=owner['npc']))

        for system in systems:
            system_data.push_back(SolarSystemData(
                id=system['id'], constellation_id=system['constellation_id'],
                region_id=system['region_id'], x=system['x'], y=system['y'],
                has_station=system['has_station'], sov_power=system['sov_power'],
                owner=system['owner'] or 0))

        for connection in connections:
            jump_data.push_back(JumpData(sys_from=connection[0], sys_to=connection[1]))

        self.c_map.load_data(owner_data, system_data, jump_data)

    cdef _retrieve_image_buffer(self):
        cdef uint8_t * data = self.c_map.retrieve_image()
        if data == NULL:
            raise MemoryError("Failed to retrieve image data")
        width = self.c_map.get_width()
        height = self.c_map.get_height()
        image_base = ImageWrapper()
        image_base.set_data(width, height, data)
        return image_base

    def get_image_as_ndarray(self):
        import numpy as np
        return np.array(self._retrieve_image_buffer(), copy=False)


    def get_image(self):
        return self._retrieve_image_buffer()
