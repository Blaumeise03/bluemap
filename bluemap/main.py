import argparse
from datetime import datetime

from typing import Any

import PIL
from PIL import ImageDraw

from bluemap.table import Table
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
                id    INT PRIMARY  KEY,
                color VARCHAR(7)   NULL,
                name  VARCHAR(255) NULL
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
) -> tuple[list[dict], list[dict], list[tuple[int, int]], list[dict], dict[int, str]]:
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
            cursor.execute("SELECT id, color, name FROM evealliances")
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
                    'name': row['name'],
                    'npc': False,
                })

            # Load systems
            cursor.execute(
                f"SELECT "
                f"  solarSystemID, "
                f"  solarSystemName, "
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
                    'name': row['solarSystemName'],
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

            # Load regions
            cursor.execute("SELECT regionID, regionName FROM mapregions")
            regions = {}
            for row in cursor.fetchall():
                regions[row['regionID']] = row['regionName']

            # Load sov changes
            cursor.execute(
                f"""
                SELECT fromAllianceID,
                       toAllianceID,
                       systemID,
                       {c_power} as `sovPower`
                FROM sovchangelog l
                         LEFT JOIN mapsolarsystems s ON s.solarSystemID = l.systemID
                         LEFT JOIN mapregions r ON r.regionID = s.regionID
                ORDER BY r.z, r.x
                """
            )
            sov_changes = []
            for row in cursor.fetchall():
                sov_changes.append({
                    'from': row['fromAllianceID'],
                    'to': row['toAllianceID'],
                    'system': row['systemID'],
                    'sov_power': row['sovPower']
                })

        return owners, systems, connections, sov_changes, regions
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

    from PIL import ImageFont

    try:
        base_font = ImageFont.truetype(r"C:\Windows\Fonts\VerdanaB.ttf")
    except OSError:
        print("Verdana font not found, using default font.")

    print("Loading data from database...")
    owners, systems, connections, sov_changes, regions = load_data_from_db(
        args.host, args.user, args.password, args.database,
        legacy=args.legacy_db)

    print("Preparing map...")
    sov_map = SovMap()
    sov_map.update_size()
    sov_map.load_data(owners, systems, connections)
    sov_map.load_old_owner_data("sovchange_2025-02-16.dat")


    start = datetime.now()
    sov_map.set_sov_power_function(
        lambda sov_power, _, __: 10.0 * (6 if sov_power >= 6.0 else sov_power / 2.0)
    )
    sov_map.calculate_influence()
    diff = datetime.now() - start
    print(f"Influence Calculation took {diff.total_seconds():.4f} seconds.")

    print("Rendering map...")
    start = datetime.now()
    sov_map.render(thread_count=16)
    diff = datetime.now() - start
    print(f"Rendering took {diff.total_seconds():.4f} seconds.")

    print("Calculating labels...")
    start = datetime.now()
    sov_map.calculate_labels()
    diff = datetime.now() - start
    print(f"Label calculation took {diff.total_seconds():.4f} seconds.")
    #labels = sov_map.get_owner_labels()
    #for label in labels:
    #    print(f"{label.owner_id}: ({label.x}, {label.y}) with {label.count} pixels")

    print("Rendering overlay...")
    import PIL.Image
    sov_layer = sov_map.get_image().as_pil_image()
    sys_layer = PIL.Image.new("RGBA", sov_layer.size, (0, 0, 0, 0))
    bg_layer = PIL.Image.new("RGBA", sov_layer.size, (0, 0, 0, 255))
    label_layer = PIL.Image.new("RGBA", bg_layer.size, (0, 0, 0, 0))
    legend_layer = PIL.Image.new("RGBA", bg_layer.size, (0, 0, 0, 0))
    sov_map.draw_systems(ImageDraw.Draw(sys_layer))
    sov_map.draw_owner_labels(ImageDraw.Draw(label_layer), base_font=base_font)

    # Draw legend
    draw = ImageDraw.Draw(legend_layer)
    table = Table((64, 64, 64, 255), fixed_col_widths=[100, 100, 40, 80])
    table.add_row(
        ["Sov. Lost", "Sov. Gain", "System", "Region"],
        [(200, 200, 200, 255)] * 4,
        anchors=["ms", "ms", "ms", "ms"]
    )
    table.add_h_line()
    for change in sov_changes:
        from_owner = sov_map.owners[change['from']] if change['from'] else None
        to_owner = sov_map.owners[change['to']] if change['to'] else None
        system = sov_map.systems[change['system']]
        table.add_row(
            [
                from_owner.name if from_owner else "",
                to_owner.name if to_owner else "",
                system.name,
                regions[system.region_id]
            ],
            [
                from_owner.color if from_owner else (0, 0, 0, 255),
                to_owner.color if to_owner else (0, 0, 0, 255),
                (200, 200, 255, 255), (200, 200, 200, 255)],
            bg_color=(0, 0, 0x40, 255) if change['sov_power'] >= 6.0 else None
        )
    table.render(draw, (10, 50))

    combined = PIL.Image.alpha_composite(sov_layer, sys_layer)
    combined = PIL.Image.alpha_composite(combined, label_layer)
    combined = PIL.Image.alpha_composite(combined, legend_layer)
    combined = PIL.Image.alpha_composite(bg_layer, combined)

    print("Saving map...")
    combined.save("influence.png")
    print("Done.")


def test_table():
    from .table import Table
    from PIL import Image, ImageDraw

    table = Table((0, 0, 0, 255))

    table.add_row(
        ["Sov. Lost", "Sov. Gain", "System", "Region"],
        [(200, 200, 200, 255)] * 4,
        anchors=["ms", "ms", "ms", "ms"]
    )
    table.add_h_line()
    table.add_row(
        ["[SHH]", "[SUS]", "J9-5MQ", "Branch"],
        [(255, 0, 0, 255), (0, 255, 0, 255), (200, 200, 255, 255), (200, 200, 200, 255)]
    )
    table.add_row(
        ["[KRKD]", "[SUS]", "EU9-J3", "Detroid"],
        [(255, 0, 0, 255), (0, 255, 0, 255), (200, 200, 255, 255), (200, 200, 200, 255)]
    )
    table.add_row(
        ["", "[NICE]", "GBT4-J", "Etherium Reach"],
        [(255, 0, 0, 255), (0, 255, 0, 255), (200, 200, 255, 255), (200, 200, 200, 255)]
    )
    table.add_row(
        ["[MSOS]", "", "U-QMOA", "Scalding Pass"],
        [(255, 0, 0, 255), (0, 255, 0, 255), (200, 200, 255, 255), (200, 200, 200, 255)]
    )
    img = PIL.Image.new("RGBA", (300, 100), (0, 0, 0, 0))
    table.render(ImageDraw.Draw(img), (20, 20))
    img.save("table.png")


if __name__ == "__main__":
    main()
