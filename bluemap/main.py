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
        #sov_map.save("sov_map.png")
        memory = process.memory_info().rss / 1024 / 1024
        diff = memory - start_memory
        print(f"Render {i} done: {memory:.2f} MB ({diff:+.2f} MB)")
        start_memory = memory
        img_buffer = sov_map.get_image()
        memory = process.memory_info().rss / 1024 / 1024
        diff = memory - start_memory
        print(f"Image {i} loaded: {memory:.2f} MB ({diff:+.2f} MB)")
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
                "SELECT solarSystemID, constellationID, regionID, x, y, z, stantion, ADM, allianceID FROM mapsolarsystems")
            systems = []
            for row in cursor.fetchall():
                systems.append({
                    'id': row['solarSystemID'],
                    'constellation_id': row['constellationID'],
                    'region_id': row['regionID'],
                    'x': row['x'],
                    'y': row['y'],
                    'z': row['z'],
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

    print("Loading data from database...")
    owners, systems, connections = load_data_from_db(args.host, args.user, args.password, args.database)
    print("Preparing map...")
    sov_map = SovMap()
    sov_map.load_data(owners, systems, connections)
    print("Rendering map...")
    sov_map.render(thread_count=16)
    print("Calculating labels...")
    labels = sov_map.calculate_labels()
    for label in labels:
        print(f"{label.owner_id}: ({label.x}, {label.y}) with {label.count} pixels")
    print("Saving map...")
    sov_map.save("influence.png")
    print("Done.")

if __name__ == "__main__":
    mem_test()
