
import unittest

import psutil

from bluemap import SovMap
from mock_data import mock_owners, mock_systems, mock_connections, mock_regions


class TestMemory(unittest.TestCase):
    leak_threshold = 1024 * 1024 * 1  # 1 MB
    # A bit of memory rise is expected because I think unittest does store test results or logs in memory
    # Running these tests just in a simple script would result in way less memory rise

    def __init__(self, *args, **kwargs):
        super(TestMemory, self).__init__(*args, **kwargs)
        self.sov_map: SovMap | None = None
        self._last_mem: int = None
        self._process = psutil.Process()

    def _start_mem_check(self):
        self._last_mem = self._process.memory_info().rss

    def _create_mock_map(self):
        self.sov_map = SovMap(width=128, height=128, offset_x=-32, offset_y=-32)
        self.sov_map.update_size(
            width=128, height=128,
        )
        self.sov_map.scale = 1 / 16.0

    def _load_mock_map(self):
        if self.sov_map is None:
            self._create_mock_map()
        self.sov_map.load_data(
            owners=mock_owners,
            systems=mock_systems,
            connections=mock_connections,
            regions=mock_regions,
        )

    def _render(self):
        worker = self.sov_map.create_workers(1)[0]
        worker.render()

    def setUp(self):
        pass

    def tearDown(self):
        self.sov_map = None

    def assertNoMemoryLeak(self, source: str):
        current_mem = self._process.memory_info().rss
        diff = current_mem - self._last_mem
        if diff > self.leak_threshold:
            diff_mb = diff / (1024 * 1024)
            self.fail(f"Memory leak in {source} detected, leaked {diff_mb:.2f} MB")
        elif diff < self.leak_threshold:
            print(f"Warning: Memory usage in {source} is negative: {current_mem / (1024 * 1024):.2f} MB ({diff / (1024 * 1024):-.2f} MB)")
        else:
            print(f"Memory usage in {source}: {current_mem / (1024 * 1024):.2f} MB ({diff / (1024 * 1024):+.2f} MB)")

    def test_constructor(self):
        for i in range(5):
            self._start_mem_check()
            for __ in range(50):
                sov_map = SovMap()
            del sov_map
            self.assertNoMemoryLeak(f"SovMap constructor #{i}")

    def test_loading(self):
        for i in range(5):
            self._start_mem_check()
            for __ in range(50):
                sov_map = SovMap()
                sov_map.load_data(
                    owners=mock_owners,
                    systems=mock_systems,
                    connections=mock_connections,
                    regions=mock_regions,
                )
            del sov_map
            self.assertNoMemoryLeak(f"SovMap.load_data #{i}")

    def test_render_image(self):
        for _ in range(5):
            self._start_mem_check()
            for __ in range(20):
                self._load_mock_map()
                self._render()
                img_buff = self.sov_map.get_image()
            del img_buff
            self.sov_map: SovMap | None = None
            self.assertNoMemoryLeak("SovMap.get_image")

    def test_owner_buffer(self):
        for _ in range(5):
            self._create_mock_map()
            self._start_mem_check()
            for __ in range(1000):
                buff = self.sov_map.get_owner_buffer()
            del buff
            self.assertNoMemoryLeak("SovMap.get_owner_buffer")
            self.sov_map: SovMap | None = None

    def test_owner_image(self):
        for _ in range(5):
            self._create_mock_map()
            self._start_mem_check()
            for __ in range(1000):
                img = self.sov_map.get_owner_image()
            del img
            self.assertNoMemoryLeak("SovMap.get_owner_image")
            self.sov_map: SovMap | None = None

    def test_func_power_falloff(self):
        class MockCallable:
            def __call__(self, value, _, __):
                return value
        for _ in range(5):
            self._create_mock_map()
            self.sov_map.set_power_falloff_function(MockCallable())
            self._start_mem_check()
            for __ in range(1000):
                self.sov_map.set_power_falloff_function(MockCallable())
            self.assertNoMemoryLeak("SovMap.set_power_falloff_function")
            self.sov_map: SovMap | None = None

    def test_func_power_falloff_error(self):
        class MockCallable:
            def __call__(self, value, _, __):
                raise Exception("Test exception")
        for _ in range(5):
            self._create_mock_map()
            self._load_mock_map()
            self.sov_map.set_power_falloff_function(MockCallable())
            self._start_mem_check()
            for __ in range(1000):
                self.sov_map.set_power_falloff_function(MockCallable())
                self.assertRaises(RuntimeError, self.sov_map.calculate_influence)
            self.assertNoMemoryLeak("SovMap.set_power_falloff_function")
            self.sov_map: SovMap | None = None

    def test_sov_power(self):
        class MockCallable:
            def __call__(self, value, _, __):
                return value
        for _ in range(5):
            self._create_mock_map()
            self.sov_map.set_sov_power_function(MockCallable())
            self._start_mem_check()
            for __ in range(1000):
                self.sov_map.set_sov_power_function(MockCallable())
            self.assertNoMemoryLeak("SovMap.set_sov_power_function")
            self.sov_map: SovMap | None = None

    def test_sov_power_error(self):
        class MockCallable:
            def __call__(self, value, _, __):
                raise Exception("Test exception")
        for _ in range(5):
            self._create_mock_map()
            self._load_mock_map()
            self.sov_map.set_sov_power_function(MockCallable())
            self._start_mem_check()
            for __ in range(1000):
                self.sov_map.set_sov_power_function(MockCallable())
                self.assertRaises(RuntimeError, self.sov_map.calculate_influence)
            self.assertNoMemoryLeak("SovMap.set_sov_power_function")
            self.sov_map: SovMap | None = None

    def test_influence_to_alpha(self):
        class MockCallable:
            def __call__(self, value):
                return value
        for _ in range(5):
            self._create_mock_map()
            self.sov_map.set_influence_to_alpha_function(MockCallable())
            self._start_mem_check()
            for __ in range(1000):
                self.sov_map.set_influence_to_alpha_function(MockCallable())
            self.assertNoMemoryLeak("SovMap.set_influence_to_alpha_function")
            self.sov_map: SovMap | None = None

    def test_influence_to_alpha_error(self):
        class MockCallable:
            def __call__(self, value):
                raise Exception("Test exception")
        for _ in range(5):
            self._create_mock_map()
            self._load_mock_map()
            self.sov_map.set_influence_to_alpha_function(MockCallable())
            self.sov_map.calculate_influence()
            worker = self.sov_map.create_workers(1)[0]
            self._start_mem_check()
            for __ in range(1000):
                self.assertRaises(RuntimeError, worker.render)
            self.assertNoMemoryLeak("SovMap.set_influence_to_alpha_function")
            self.sov_map: SovMap | None = None

    def test_labels(self):
        for _ in range(5):
            self._create_mock_map()
            self._load_mock_map()
            self._render()
            self._start_mem_check()
            for __ in range(1000):
                self.sov_map.calculate_labels()
                lbls = self.sov_map.get_owner_labels()
            del lbls
            self.assertNoMemoryLeak("SovMap.calculate_labels")
            self.sov_map: SovMap | None = None


if __name__ == '__main__':
    unittest.main()
