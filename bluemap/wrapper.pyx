# distutils: language = c++
import weakref

from libc.stdlib cimport free
from libcpp.string cimport string
from libcpp.vector cimport vector

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

        CMap.CColumnWorker * create_worker(unsigned int start_x, unsigned int end_x) except +

        void render_multithreaded() except +
        void calculate_influence() except +
        void load_data(const string& filename) except +
        void load_data(const vector[COwnerData]& owners,
                       const vector[CSolarSystemData]& solar_systems,
                       const vector[CJumpData]& jumps) except +
        void save(const string& path) except +

        uint8_t *retrieve_image() except +
        id_t *create_owner_image() except +

        unsigned int get_width()
        unsigned int get_height()

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


cdef class ImageWrapper:
    cdef void * data_ptr
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

    cdef set_data(self, int width, int height, void * data_ptr):
        self.data_ptr = data_ptr
        self.width = width
        self.height = height

    def __dealloc__(self):
        free(self.data_ptr)
        self.data_ptr = NULL

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

    def as_ndarray(self):
        import numpy as np
        return np.array(self, copy=False)

    def as_pil_image(self):
        import PIL.Image
        return PIL.Image.frombuffer('RGBA', (self.width, self.height), self, 'raw', 'RGBA', 0, 1)

    @property
    def size(self):
        return self.width, self.height

cdef class ColumnWorker:
    cdef CMap.CColumnWorker * c_worker
    cdef object _map

    def __cinit__(self, Map map_, unsigned int start_x, unsigned int end_x):
        if not map:
            raise ValueError("Map is not initialized")
        self.c_worker = map_.c_map.create_worker(start_x, end_x)
        self._map = weakref.proxy(map_)
        self._map._add_worker(self)

    def __dealloc__(self):
        try:
            self._map._remove_worker(self)
        except ReferenceError:
            pass
        del self.c_worker

    def _free(self):
        del self.c_worker
        self.c_worker = NULL

    def render(self) -> None:
        if not self.c_worker:
            raise ReferenceError("The sov map corresponding to this worker has been deallocated")
        with nogil:
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

cdef class Map:
    cdef CMap * c_map
    cdef int _calculated
    cdef object workers

    cdef object __weakref__

    cdef long long width
    cdef long long height
    cdef long long offset_x
    cdef long long offset_y
    cdef double scale

    _owners: dict[int, Owner]
    _systems: dict[int, SolarSystem]
    _connections: list[tuple[int, int]]

    def __init__(
            self,
            width: int = 928 * 2, height: int = 1024 * 2,
            offset_x: int = 208, offset_y: int = 0):
        self.width = width
        self.height = height
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.scale = 4.8445284569785E17 / ((self.width - 20) / 2.0)
        self._owners = {}
        self._systems = {}
        self._connections = []

    def __cinit__(self):
        self.c_map = new CMap()
        self._calculated = False
        self.workers = []

    def __dealloc__(self):
        for worker in self.workers:
            self._remove_worker(worker)
            worker._free()
            del worker
        del self.c_map

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

    @property
    def owners(self):
        return self._owners

    @property
    def systems(self):
        return self._systems

    @property
    def connections(self):
        return self._connections

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
            owner_data.push_back(owner_obj.c_data)

        cdef double x, y, z, width, height, offset_x, offset_y, scale
        offset_x = self.offset_x
        offset_y = self.offset_y
        scale = self.scale
        width = self.width
        height = self.height
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
            system_data.push_back(system_obj.c_data)

        for connection in connections:
            if connection[0] in skipped or connection[1] in skipped:
                continue
            jump_data.push_back(CJumpData(sys_from=connection[0], sys_to=connection[1]))
            self._connections.append(connection)

        self.c_map.load_data(owner_data, system_data, jump_data)
        print("Skipped %d systems" % len(skipped))

    cdef _retrieve_image_buffer(self):
        cdef uint8_t * data = self.c_map.retrieve_image()
        if data == NULL:
            return None
        width = self.c_map.get_width()
        height = self.c_map.get_height()
        image_base = ImageWrapper()
        image_base.set_data(width, height, data)
        return image_base

    def get_image_as_ndarray(self):
        return self._retrieve_image_buffer().as_ndarray()

    def get_image(self) -> ImageWrapper | None:
        """
        Get the image as a buffer. This method will remove the image from the map, further calls to this method will
        return None.

        The image buffer can be passed to PIL.Image.frombuffer to create an image:

        >>> image = map.get_image()
        >>> img = PIL.Image.frombuffer('RGBA', image.size, image, 'raw', 'RGBA', 0, 1)

        Or to create a numpy array:
        >>> image = map.get_image().as_ndarray()

        :return: the image buffer if available, None otherwise
        """
        return self._retrieve_image_buffer()
