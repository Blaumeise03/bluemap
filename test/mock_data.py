from typing import Any

mock_owners = [
    {'id': 1, 'color': (255, 0, 0, 255), 'name': 'Alliance Red', 'npc': False},
    {'id': 2, 'color': (0, 255, 0, 255), 'name': 'Alliance Green', 'npc': False},
    {'id': 3, 'color': (0, 0, 255, 255), 'name': 'Alliance Blue', 'npc': False},
    {'id': 4, 'color': (255, 255, 0, 255), 'name': 'Alliance Yellow', 'npc': False},
]

mock_systems = [
    {'id': 100, 'name': 'System A', 'constellation_id': 10, 'region_id': 1, 'x': 0.0, 'y': 0.0, 'z': 0.0, 'has_station': True, 'sov_power': 5.0, 'owner': 1},
    {'id': 101, 'name': 'System B', 'constellation_id': 10, 'region_id': 1, 'x': 1.0, 'y': 0.0, 'z': 1.0, 'has_station': False, 'sov_power': 3.0, 'owner': 2},
    {'id': 102, 'name': 'System C', 'constellation_id': 11, 'region_id': 1, 'x': 2.0, 'y': 0.0, 'z': 2.0, 'has_station': True, 'sov_power': 4.0, 'owner': 3},
    {'id': 103, 'name': 'System D', 'constellation_id': 11, 'region_id': 2, 'x': 3.0, 'y': 0.0, 'z': 3.0, 'has_station': False, 'sov_power': 2.0, 'owner': 1},
    {'id': 104, 'name': 'System E', 'constellation_id': 12, 'region_id': 2, 'x': 4.0, 'y': 0.0, 'z': 4.0, 'has_station': True, 'sov_power': 6.0, 'owner': 4},
    {'id': 105, 'name': 'System F', 'constellation_id': 12, 'region_id': 2, 'x': 5.0, 'y': 0.0, 'z': 0.0, 'has_station': False, 'sov_power': 2.0, 'owner': 3},
    # System outside of bounds
    {'id': 106, 'name': 'System G', 'constellation_id': 12, 'region_id': 2, 'x': 12.0, 'y': 0.0, 'z': 0.0, 'has_station': False, 'sov_power': 2.0, 'owner': 3},
    # Invalid system (no coordinates)
    {'id': 107, 'name': 'System H', 'constellation_id': 12, 'region_id': 2, 'x': None, 'y': None, 'z': None, 'has_station': False, 'sov_power': 2.0, 'owner': 3},
]

def alternative_owners() -> list[dict[str, Any]]:
    # Blue alliance is now red
    return list(map(lambda sys: {
        **sys,
        'owner': 1 if sys['owner'] == 3 else sys['owner'],
    }, mock_systems))

mock_connections = [
    (100, 101),
    (101, 102),
    (102, 103),
    (103, 104),
    (104, 105),
    (105, 100),
    (100, 102),
    (101, 103),
    (102, 104),
    (103, 105),
    (104, 100),
    (105, 101),
    # Connections to invalid systems
    (100, 106),
    (106, 107),
    (107, 100),
]

mock_regions = [
   {'id': 1, 'name': 'Region Alpha', 'x': 0.0, 'y': 0.0, 'z': 0.0},
   {'id': 2, 'name': 'Region Beta', 'x': 4.0, 'y': 0.0, 'z': 4.0},
    # Region outside of bounds
    {'id': 3, 'name': 'Region Gamma', 'x': 12.0, 'y': 0.0, 'z': 0.0},
    # Invalid region (no coordinates)
    {'id': 4, 'name': 'Region Delta', 'x': None, 'y': None, 'z': None},
]

mock_sov_changes = [
    {'from': 1, 'to': 2, 'system': 100, 'sov_power': 5.0},
    {'from': 2, 'to': 3, 'system': 101, 'sov_power': 3.0},
    {'from': 3, 'to': 1, 'system': 102, 'sov_power': 4.0},
    {'from': 1, 'to': 4, 'system': 103, 'sov_power': 2.0},
    {'from': 4, 'to': 2, 'system': 104, 'sov_power': 6.0},
]