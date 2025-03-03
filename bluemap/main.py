import argparse

from typing import Any

import PIL
from PIL import ImageDraw

from . import SovMap, OwnerImage


def _mem_test():
    """
    Test memory safety of the SovMap class.
    :return:
    """
    import psutil
    process = psutil.Process()
    start_memory = process.memory_info().rss / 1024 / 1024
    for i in range(5):
        sov_map = SovMap()
        sov_map.load_data_from_file("dump.dat")
        sov_map.render(thread_count=16)
        # sov_map.save("sov_map.png")
        memory = process.memory_info().rss / 1024 / 1024
        diff = memory - start_memory
        print(f"Render {i} done: {memory:.2f} MB ({diff:+.2f} MB)")
        start_memory = memory
        img_buffer = sov_map.get_image()
        img_owner = sov_map.get_owner_map()
        memory = process.memory_info().rss / 1024 / 1024
        diff = memory - start_memory
        print(f"Image {i} loaded: {memory:.2f} MB ({diff:+.2f} MB)")
        start_memory = memory


def _create_tables(connection, legacy=False):
    from pymysql import cursors
    col_station = "station" if not legacy else "stantion"
    col_power = "sovPower" if not legacy else "ADM"
    with connection.cursor() as cursor:  # type: cursors.Cursor
        cursor.execute(
            # MariaDB
            f"""
            CREATE TABLE IF NOT EXISTS evealliances
            (
                id    INT PRIMARY KEY,
                color VARCHAR(7)
            )
            """)
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS mapsolarsystems
            (
                solarSystemID   INT PRIMARY KEY,
                constellationID INT,
                regionID        INT,
                x               FLOAT,
                y               FLOAT,
                z               FLOAT,
                {col_station}   BOOLEAN,
                {col_power}     FLOAT,
                allianceID      INT
            )
            """)
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS mapsolarsystemjumps
            (
                fromSolarSystemID INT,
                toSolarSystemID   INT,
                PRIMARY KEY (fromSolarSystemID, toSolarSystemID)
            )
            """)


def load_data_from_db(
        host, user, password, database, legacy=False
) -> tuple[list[dict], list[dict], list[tuple[int, int]]]:
    import pymysql
    from pymysql import cursors
    c_station = "station" if not legacy else "stantion"
    c_power = "sovPower" if not legacy else "ADM"
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
            cursor.execute("SELECT id, color FROM evealliances")
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
                f"SELECT "
                f"  solarSystemID, "
                f"  constellationID, "
                f"  regionID, x, y, z,"
                f"  {c_station} as `station`,"
                f"  {c_power} as `sovPower`,"
                f"  allianceID "
                f"FROM mapsolarsystems")
            systems = []
            for row in cursor.fetchall():
                systems.append({
                    'id': row['solarSystemID'],
                    'constellation_id': row['constellationID'],
                    'region_id': row['regionID'],
                    'x': row['x'],
                    'y': row['y'],
                    'z': row['z'],
                    'has_station': row['station'] == 1,
                    'sov_power': row['sovPower'],
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
    parser.add_argument("--legacy_db", action="store_true", help="Use legacy database schema")
    args = parser.parse_args()

    print("Loading data from database...")
    owners, systems, connections = load_data_from_db(
        args.host, args.user, args.password, args.database,
        legacy=args.legacy_db)
    print("Preparing map...")
    sov_map = SovMap()
    sov_map.update_size()
    sov_map.load_data(owners, systems, connections)
    sov_map.load_old_owner_data("sovchange_2025-02-16.dat")
    print("Rendering map...")
    sov_map.render(thread_count=16)
    print("Calculating labels...")
    labels = sov_map.calculate_labels()
    for label in labels:
        print(f"{label.owner_id}: ({label.x}, {label.y}) with {label.count} pixels")
    print("Saving map...")
    import PIL.Image
    sov_layer = sov_map.get_image().as_pil_image()
    sys_layer = PIL.Image.new("RGBA", sov_layer.size, (0, 0, 0, 0))
    bg_layer = PIL.Image.new("RGBA", sov_layer.size, (0, 0, 0, 255))
    sov_map.draw_systems(ImageDraw.Draw(sys_layer))
    combined = PIL.Image.alpha_composite(sov_layer, sys_layer)
    combined = PIL.Image.alpha_composite(bg_layer, combined)
    combined.save("influence.png")
    print("Done.")


if __name__ == "__main__":
    main()
