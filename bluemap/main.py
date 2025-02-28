import argparse

from typing import Any

import PIL
from PIL.Image import Image

from bluemap.map import SovMap


def mem_test():
    import psutil
    process = psutil.Process()
    start_memory = process.memory_info().rss / 1024 / 1024
    for i in range(5):
        sov_map = SovMap()
        sov_map.load_data_from_file("dump.dat")
        sov_map.render(thread_count=16)
        sov_map.save("sov_map.png")
        memory = process.memory_info().rss / 1024 / 1024
        diff = memory - start_memory
        print(f"Render {i} done: {memory:.2f} MB ({diff:+.2f} MB)")
        start_memory = memory
        raw = sov_map._map.get_image_as_ndarray()
        img = PIL.Image.fromarray(raw, "RGBA")
        img.save("sov_map2.png")
        memory = process.memory_info().rss / 1024 / 1024
        diff = memory - start_memory
        print(f"Image {i} saved: {memory:.2f} MB ({diff:+.2f} MB)")
        start_memory = memory


def load_data_from_db(host, user, password, database) -> tuple[list[dict], list[dict], list[tuple[int, int]]]:
    import pymysql
    from pymysql import cursors
    # Database connection parameters
    connection = pymysql.connect(
        host=host,
        user=user,
        password=password,
        database=database,
        cursorclass=pymysql.cursors.DictCursor
    )

    width = 928 * 2
    height = 1024 * 2
    scale = 4.8445284569785E17 / ((width - 20) / 2.0)

    try:
        with connection.cursor() as cursor:
            # Load owners (alliances)
            cursor.execute("SELECT id, color, onMap FROM evealliances")
            owners = []
            for row in cursor.fetchall():  # type: dict[str, Any]
                if row['color'] is not None:
                    color = row['color'].lstrip('#')
                    color = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4)) + (255,) if color else (0, 0, 0, 255)
                else:
                    color = (0, 0, 0, 255)
                owners.append({
                    'id': row['id'],
                    'color': color,
                    'npc': False,
                })

            # Load systems
            cursor.execute(
                "SELECT solarSystemID, constellationID, regionID, x, z, stantion, ADM, allianceID FROM mapsolarsystems")
            systems = []
            for row in cursor.fetchall():
                systems.append({
                    'id': row['solarSystemID'],
                    'constellation_id': row['constellationID'],
                    'region_id': row['regionID'],
                    'x': int((((row['x'] or 0) / scale) + width / 2 + 208) + 0.5),
                    'y': int((((row['z'] or 0) / scale) + height / 2 + 0) + 0.5),
                    'has_station': row['stantion'] == 1,
                    'sov_power': row['ADM'],
                    'owner': row['allianceID'],
                })

            # Load connections (jumps)
            cursor.execute("SELECT fromSolarSystemID, toSolarSystemID FROM mapsolarsystemjumps")
            connections = []
            for row in cursor.fetchall():
                connections.append((row['fromSolarSystemID'], row['toSolarSystemID']))

        return owners, systems, connections
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description='Load data from MariaDB and render SovMap.')
    parser.add_argument('--host', required=True, help='Database host')
    parser.add_argument('--user', required=True, help='Database user')
    parser.add_argument('--password', required=True, help='Database password')
    parser.add_argument('--database', required=True, help='Database name')
    args = parser.parse_args()

    owners, systems, connections = load_data_from_db(args.host, args.user, args.password, args.database)
    sov_map = SovMap()
    sov_map.load_data(owners, systems, connections)
    sov_map.render(thread_count=16)
    sov_map.save("sov_map.png")

if __name__ == "__main__":
    mem_test()
