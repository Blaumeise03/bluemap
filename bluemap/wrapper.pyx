# distutils: language = c++
import weakref

from libcpp.string cimport string
from libcpp.vector cimport vector

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
            void render() nogil

        Map() except +
        # unsigned int width
        # unsigned int height
        # unsigned int offset_x
        # unsigned int offset_y
        # double scale
        # double power_falloff

        CMap.CColumnWorker * create_worker(unsigned int start_x, unsigned int end_x)

        void render_multithreaded()
        void calculate_influence()
        void load_data(const string& filename)
        void load_data(const vector[OwnerData]& owners,
                       const vector[SolarSystemData]& solar_systems,
                       const vector[JumpData]& jumps)
        void save(const string& path)

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
