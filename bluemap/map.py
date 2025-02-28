
import os

from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path

from bluemap.wrapper import Map, ColumnWorker


class SovMap:
    def __init__(self):

        self._map = Map()

    def load_data_from_file(self, path: str):
        self._map.load_data_from_file(path)

    def load_data(self, owner_data: list[dict], system_data: list[dict], jump_data: list[tuple[int, int]]):
        self._map.load_data(owner_data, system_data, jump_data)

    def render(self, thread_count: int = 1):
        if not self._map.calculated:
            self._map.calculate_influence()
        with ThreadPoolExecutor(max_workers=thread_count) as pool:
            workers = self._map.create_workers(thread_count)
            pool.map(ColumnWorker.render, workers)


    def save(self, path: Path | os.PathLike[str] | str):
        if not isinstance(path, Path):
            path = Path(path)
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        self._map.save(str(path.absolute()))
