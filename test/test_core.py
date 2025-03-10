import unittest

import PIL
import numpy as np
from PIL import Image, ImageDraw

from bluemap import SovMap, SolarSystem, Region, Owner
from bluemap._map import Constellation
from mock_data import mock_owners, mock_systems, mock_connections, mock_regions, alternative_owners


class TestSovMap(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestSovMap, self).__init__(*args, **kwargs)
        self.sov_map: SovMap | None = None

    def _create_mock_map(self, alternate=False):
        self.sov_map = SovMap(width=128, height=128, offset_x=-32, offset_y=-32)
        self.sov_map.update_size(
            width=128, height=128, sample_rate=8,
        )
        self.sov_map.scale = 1 / 16.0
        self.sov_map.load_data(
            owners=mock_owners,
            systems=mock_systems if not alternate else alternative_owners(),
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

    def assertColorAlmostEqual(self, img: np.ndarray, x, y, color, delta):
        actual = (img[y, x, 0], img[y, x, 1], img[y, x, 2], img[y, x, 3])
        self.assertAlmostEqual(actual[0], color[0], delta=delta,
                               msg=f"Expected color {color} at px {x}/{y}, got {actual} (diff at r)")
        self.assertAlmostEqual(actual[1], color[1], delta=delta,
                               msg=f"Expected color {color} at px {x}/{y}, got {actual} (diff at g)")
        self.assertAlmostEqual(actual[2], color[2], delta=delta,
                               msg=f"Expected color {color} at px {x}/{y}, got {actual} (diff at b)")
        self.assertAlmostEqual(actual[3], color[3], delta=delta,
                               msg=f"Expected color {color} at px {x}/{y}, got {actual} (diff at a)")

    def test_creation(self):
        self._create_mock_map()

    def test_getter_setter(self):
        self._create_mock_map()
        self.assertEqual(self.sov_map.width, 128)
        self.assertEqual(self.sov_map.height, 128)
        self.assertEqual(self.sov_map.offset_x, -32)
        self.assertEqual(self.sov_map.offset_y, -32)
        self.assertEqual(self.sov_map.sample_rate, 8)

        self.sov_map.width = 256
        self.sov_map.height = 256
        self.sov_map.sample_rate = 16
        self.sov_map.scale = 1 / 32.0

        self.assertEqual(self.sov_map.width, 256)
        self.assertEqual(self.sov_map.height, 256)
        self.assertEqual(self.sov_map.scale, 1 / 32.0)
        self.assertEqual(self.sov_map.sample_rate, 16)

        self.assertFalse(self.sov_map.calculated)
        self.sov_map.calculate_influence()
        self.assertTrue(self.sov_map.calculated)
        self._render()

        img = self.sov_map.get_image().as_pil_image()
        self.assertEqual(img.width, 256)
        self.assertEqual(img.height, 256)
        owner_buff = self.sov_map.get_owner_buffer()
        self.assertEqual(owner_buff.size[0], 256)
        self.assertEqual(owner_buff.size[1], 256)

        self.assertEqual(self.sov_map.resolution, (256, 256))
        self.sov_map.resolution = (128, 128)
        self.assertEqual(self.sov_map.resolution, (128, 128))
        owner_buff = self.sov_map.get_owner_buffer()
        self.assertEqual(owner_buff.size[0], 128)
        self.assertEqual(owner_buff.size[1], 128)

        self.assertEqual(len(self.sov_map.owners), 4)
        self.assertEqual(len(self.sov_map.systems), 6)
        self.assertEqual(len(self.sov_map.connections), 12)

    def test_render(self):
        self._create_mock_map()
        self.sov_map.calculate_influence()
        self._render()
        sov_buff = self.sov_map.get_image()
        sov_layer = sov_buff.as_pil_image()
        sov_arr = sov_buff.as_ndarray()

        # Test some pixels
        # Center of red alliance
        self.assertColorAlmostEqual(sov_arr, 36, 32, (255, 0, 0, 40), delta=1.5)
        # Border of red alliance
        self.assertColorAlmostEqual(sov_arr, 2, 37, (255, 0, 0, 72), delta=1.5)
        # Outside of alliances
        self.assertColorAlmostEqual(sov_arr, 1, 38, (0, 0, 0, 0), delta=1.5)
        # Blue alliance
        self.assertColorAlmostEqual(sov_arr, 50, 69, (0, 0, 255, 25), delta=1.5)
        # Yellow alliance
        self.assertColorAlmostEqual(sov_arr, 96, 96, (255, 255, 0, 78), delta=1.5)

        sov_layer.save("test_sov_layer.png")

        sys_layer = PIL.Image.new("RGBA", sov_layer.size, (0, 0, 0, 0))
        sys_draw = PIL.ImageDraw.Draw(sys_layer)
        self.sov_map.draw_systems(sys_draw)
        self.sov_map.draw_region_labels(sys_draw)
        self.sov_map.calculate_labels()

        expected_labels = [
            (1, 53, (37, 39)),
            (4, 106, (97, 76)),
            (3, 17, (66, 66)),
        ]
        self.assertCountEqual(
            expected_labels,
            list(map(lambda o: (o.owner_id, o.count, (o.x, o.y)),
                     self.sov_map.get_owner_labels())),
            "Owner labels are not as expected")

        self.sov_map.draw_owner_labels(sys_draw)
        bg_layer = PIL.Image.new("RGBA", sov_layer.size, (0, 0, 0, 255))
        combined = PIL.Image.alpha_composite(sov_layer, sys_layer)
        combined = PIL.Image.alpha_composite(bg_layer, combined)
        combined.save("test_render.png")

    def test_old_owner(self):
        for comp in (False, True):
            self._create_mock_map()
            self.sov_map.calculate_influence()
            self._render()
            self.sov_map.save_owner_data("owner.dat", compress=comp)

            self._create_mock_map(alternate=True)
            self.sov_map.load_old_owner_data("owner.dat")
            self.sov_map.calculate_influence()
            self._render()

            sov_buff = self.sov_map.get_image()
            sov_layer = sov_buff.as_pil_image()
            sov_arr = sov_buff.as_ndarray()
            sov_layer.save("test_sov_layer2.png")

            # Test some pixels
            # Changed from red to blue (stripes)
            self.assertColorAlmostEqual(sov_arr, 55, 70, (0, 0, 255, 50), delta=1.5)
            self.assertColorAlmostEqual(sov_arr, 55, 69, (255, 0, 0, 51), delta=1.5)
            # Changed from yellow to red (stripes)
            self.assertColorAlmostEqual(sov_arr, 68, 87, (255, 255, 0, 43), delta=1.5)
            self.assertColorAlmostEqual(sov_arr, 68, 86, (255, 0, 0, 44), delta=1.5)

    def test_render_multithreaded(self):
        self._create_mock_map()
        self.sov_map.calculate_influence()
        self.sov_map.render(2)
        self.assertRaises(ValueError, lambda: self.sov_map.save("test_render_mt_pil.png", strategy="blabla"))
        self.sov_map.save("test_render_mt_pil.png", strategy="PIL")
        self.assertRaises(RuntimeError, lambda:  self.sov_map.save("test_render_mt_pil.png", strategy="PIL"))
        self.sov_map.render(2)
        self.sov_map.save("test_render_mt_cv2.png", strategy="cv2")
        self.assertRaises(RuntimeError, lambda: self.sov_map.save("test_render_mt_cv2.png", strategy="cv2"))


class TestSolarSystem(unittest.TestCase):

    def setUp(self):
        self.solar_system = SolarSystem(
            id_=1, constellation_id=2, region_id=3, x=100, y=200,
            has_station=True, sov_power=5.0, owner=10
        )

    def test_initialization(self):
        self.assertEqual(self.solar_system.id, 1)
        self.assertEqual(self.solar_system.constellation_id, 2)
        self.assertEqual(self.solar_system.region_id, 3)
        self.assertEqual(self.solar_system.x, 100)
        self.assertEqual(self.solar_system.y, 200)
        self.assertTrue(self.solar_system.has_station)
        self.assertEqual(self.solar_system.sov_power, 5.0)
        self.assertEqual(self.solar_system.owner, 10)
        self.assertEqual(self.solar_system.name, "1")

    def test_invalid_initialization(self):
        with self.assertRaises(TypeError):
            SolarSystem(id_="1", constellation_id=2, region_id=3, x=100, y=200, has_station=True, sov_power=5.0, owner=10)
        with self.assertRaises(TypeError):
            SolarSystem(id_=1, constellation_id="2", region_id=3, x=100, y=200, has_station=True, sov_power=5.0, owner=10)
        with self.assertRaises(TypeError):
            SolarSystem(id_=1, constellation_id=2, region_id="3", x=100, y=200, has_station=True, sov_power=5.0, owner=10)
        with self.assertRaises(TypeError):
            SolarSystem(id_=1, constellation_id=2, region_id=3, x="100", y=200, has_station=True, sov_power=5.0, owner=10)
        with self.assertRaises(TypeError):
            SolarSystem(id_=1, constellation_id=2, region_id=3, x=100, y="200", has_station=True, sov_power=5.0, owner=10)
        with self.assertRaises(TypeError):
            SolarSystem(id_=1, constellation_id=2, region_id=3, x=100, y=200, has_station="True", sov_power=5.0, owner=10)
        with self.assertRaises(TypeError):
            SolarSystem(id_=1, constellation_id=2, region_id=3, x=100, y=200, has_station=True, sov_power="5.0", owner=10)
        with self.assertRaises(TypeError):
            SolarSystem(id_=1, constellation_id=2, region_id=3, x=100, y=200, has_station=True, sov_power=5.0, owner="10")

    def test_name_property(self):
        self.solar_system.name = "NewName"
        self.assertEqual(self.solar_system.name, "NewName")


class TestConstellation(unittest.TestCase):

    def setUp(self):
        self.constellation = Constellation(id_=1, region_id=2, name="Orion")

    def test_initialization(self):
        self.assertEqual(self.constellation.id, 1)
        self.assertEqual(self.constellation.region_id, 2)
        self.assertEqual(self.constellation.name, "Orion")

    def test_invalid_initialization(self):
        with self.assertRaises(TypeError):
            Constellation(id_="1", region_id=2, name="Orion")
        with self.assertRaises(TypeError):
            Constellation(id_=1, region_id="2", name="Orion")

class TestRegion(unittest.TestCase):

    def setUp(self):
        self.region = Region(id_=1)

    def test_initialization(self):
        self.assertEqual(self.region.id, 1)
        self.assertEqual(self.region.name, "1")
        self.assertEqual(self.region.x, 0)
        self.assertEqual(self.region.y, 0)

    def test_invalid_initialization(self):
        with self.assertRaises(TypeError):
            Region(id_="1")

class TestOwner(unittest.TestCase):

    def setUp(self):
        self.owner = Owner(id_=1, color=(255, 0, 0), npc=True)

    def test_initialization(self):
        self.assertEqual(self.owner.id, 1)
        self.assertEqual(self.owner.color, (255, 0, 0, 255))
        self.assertTrue(self.owner.npc)
        self.assertEqual(self.owner.name, "1")

    def test_invalid_initialization(self):
        with self.assertRaises(TypeError):
            Owner(id_="1", color=(255, 0, 0), npc=True)
        with self.assertRaises(TypeError):
            Owner(id_=1, color=(255, 0, 0), npc="True")
        with self.assertRaises(ValueError):
            Owner(id_=1, color=(255, 0), npc=True)
        with self.assertRaises(ValueError):
            Owner(id_=1, color=(255, 0, 0, 0, 0), npc=True)

    def test_name_property(self):
        self.owner.name = "NewOwner"
        self.assertEqual(self.owner.name, "NewOwner")


if __name__ == '__main__':
    unittest.main()
