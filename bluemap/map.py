import os

from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path

from bluemap.wrapper import Map, ColumnWorker, SolarSystem, Owner, ImageWrapper, MapOwnerLabel


class SovMap:
    def __init__(self):
        # Do not mess around with the underlying Map object, it's not meant to be used directly
        self._map = Map()

    def load_data_from_file(self, path: str) -> None:
        self._map.load_data_from_file(path)

    def load_data(self, owner_data: list[dict], system_data: list[dict], jump_data: list[tuple[int, int]]) -> None:
        """
        Load data into the map. Only systems inside the map will be saved, other systems will be ignored.

        :param owner_data: a list of owner data, each entry is a dict with the keys 'id' (int), 'color' (3-tuple) and 'npc' (bool)
        :param system_data: a list of system data, each entry is a dict with the keys 'id', 'x', 'z', 'constellation_id', 'region_id', 'has_station', 'sov_power' and 'owner'
        :param jump_data: a list of jump data, each entry is a tuple of two system IDs
        :return:
        """
        self._map.load_data(owner_data, system_data, jump_data)

    def render(self, thread_count: int = 1) -> None:
        """
        Render the map. This method will calculate the influence of each owner and render the map. The rendering is done
        in parallel using the given number of threads.

        Warning: Calling this method while a rendering is already in progress is not safe and is considered undefined
        behavior.
        :param thread_count:
        :return:
        """
        if not self._map.calculated:
            self._map.calculate_influence()
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
            workers = self._map.create_workers(thread_count)
            pool.map(ColumnWorker.render, workers)

    def calculate_labels(self) -> list[MapOwnerLabel]:
        return self._map.calculate_labels()

    @property
    def solar_systems(self) -> dict[int, SolarSystem]:
        """
        Get a dictionary of all solar systems in the map. The key is the system ID, the value is the SolarSystem object.

        Modifications to the dict or the SolarSystem objects will not be reflected in the map. Modifications might
        cause unexpected behavior.
        :return:
        """
        return self._map.systems

    @property
    def owners(self) -> dict[int, Owner]:
        """
        Get a dictionary of all owners in the map. The key is the owner ID, the value is the Owner object.

        Modifications to the dict or the Owner objects will not be reflected in the map. Modifications might cause
        unexpected behavior.
        :return:
        """
        return self._map.owners

    @property
    def jumps(self) -> list[tuple[int, int]]:
        """
        Get a list of all connections in the map. Each connection is a tuple of two system IDs.

        Modifications to the list will not be reflected in the map. Modifications might cause unexpected behavior.
        :return:
        """
        return self._map.connections

    @property
    def width(self) -> int:
        """
        The width of the map in pixels.
        :return:
        """
        return self._map.width

    @width.setter
    def width(self, value: int) -> None:
        self._map.width = value

    @property
    def height(self) -> int:
        """
        The height of the map in pixels.
        :return:
        """
        return self._map.height

    @height.setter
    def height(self, value: int) -> None:
        self._map.height = value

    @property
    def resolution(self) -> tuple[int, int]:
        """
        The resolution of the map in pixels.
        :return:
        """
        return self._map.resolution

    @resolution.setter
    def resolution(self, value: tuple[int, int]) -> None:
        self._map.resolution = value

    @property
    def scale(self) -> float:
        """
        The scale of the map. Warning: The scale is recalculated every time the other properties are changed. So if you
        want to use a custom scale, set it last.
        :return:
        """
        return self._map.scale

    @scale.setter
    def scale(self, value: float) -> None:
        self._map.scale = value

    def get_image(self) -> ImageWrapper | None:
        """
        Get the image as a buffer. This method will remove the image from the map, further calls to this method will
        return None.

        The image buffer can be passed to PIL.Image.frombuffer to create an image:

        >>> image = sov_map.get_image().as_pil_image()

        Or to create a numpy array:
        >>> image = sov_map.get_image().as_ndarray()

        :return: the image buffer if available, None otherwise
        """
        return self._map.get_image()

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
