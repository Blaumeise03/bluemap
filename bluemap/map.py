
import os

from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path

from bluemap.wrapper import Map, ColumnWorker, SolarSystem, Owner, ImageWrapper


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
        if not self._map.calculated:
            self._map.calculate_influence()
        with ThreadPoolExecutor(max_workers=thread_count) as pool:
            workers = self._map.create_workers(thread_count)
            pool.map(ColumnWorker.render, workers)

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
