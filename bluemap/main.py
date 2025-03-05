import argparse
from datetime import datetime

from typing import Any

from bluemap.table import Table
from . import SovMap, OwnerImage


def _mem_test():
    """
    Test memory safety of the SovMap class.
    :return:
    """

    class TestCallable:
        def __call__(self, sov_power, _, __):
            return 10.0 * (6 if sov_power >= 6.0 else sov_power / 2.0)

    import psutil
    process = psutil.Process()
    start_memory = process.memory_info().rss / 1024 / 1024
    for i in range(5):
        sov_map = SovMap()
        sov_map.load_data_from_file("dump.dat")
        # for j in range(100):
        # sov_map.set_sov_power_function(lambda sov_power, _, __: 10.0 * (6 if sov_power >= 6.0 else sov_power / 2.0))
        # sov_map.set_sov_power_function(TestCallable())
        sov_map.render(thread_count=16)
        # sov_map.save("sov_map.png")
        memory = process.memory_info().rss / 1024 / 1024
        diff = memory - start_memory
        print(f"Render {i} done: {memory:.2f} MB ({diff:+.2f} MB)")
        start_memory = memory
        img_buffer = sov_map.get_image()
        img_owner = sov_map.get_owner_buffer()
        memory = process.memory_info().rss / 1024 / 1024
        diff = memory - start_memory
        print(f"Image {i} loaded: {memory:.2f} MB ({diff:+.2f} MB)")
        start_memory = memory


def _create_tables(connection):
    from pymysql import cursors
    with connection.cursor() as cursor:  # type: cursors.Cursor
        cursor.execute(
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
                solarSystemName VARCHAR(255),
                constellationID INT,
                regionID        INT,
                x               FLOAT,
                y               FLOAT,
                z               FLOAT,
                station         BOOLEAN,
                sovPower        FLOAT,
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
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS mapregions
            (
                regionID   INT PRIMARY KEY,
                regionName VARCHAR(255),
                x          FLOAT,
                y          FLOAT,
                z          FLOAT
            )
            """)
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS sovchangelog
            (
                fromAllianceID INT,
                toAllianceID   INT,
                systemID       INT,
                sovPower       FLOAT
            )
            """)


def load_data_from_db(
        host, user, password, database
) -> tuple[list[dict], list[dict], list[tuple[int, int]], list[dict], dict[int, dict]]:
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
                f"  station,"
                f"  sovPower,"
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
            cursor.execute("SELECT regionID, regionName, x, y, z FROM mapregions")
            regions = {}
            for row in cursor.fetchall():
                regions[row['regionID']] = {
                    'id': row['regionID'],
                    'name': row['regionName'],
                    'x': row['x'],
                    'y': row['y'],
                    'z': row['z'],
                }
            # Load sov changes
            cursor.execute(
                f"""
                SELECT fromAllianceID,
                       toAllianceID,
                       systemID,
                       sovPower
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
    parser = argparse.ArgumentParser(description='Load data from MariaDB and render the influence map.')
    parser.add_argument('--host', required=True, help='Database host')
    parser.add_argument('--user', required=True, help='Database user')
    parser.add_argument('--password', required=True, help='Database password')
    parser.add_argument('--database', required=True, help='Database name')
    parser.add_argument('--text', action='append', nargs='*',
                        help='Text to render in the top left corner. Use --text header "content" for a bold line, '
                             'or --text "content" for a normal line. For empty lines, use --text "" or without any '
                             'extra arg.')
    parser.add_argument('--output', '-o', default='influence.png', help='Output file name for the image')
    parser.add_argument('--map_out', '-mo', required=False,
                        help='Output file name for the map. This output should be provided as input for the next render'
                             ' to render changed areas.')
    parser.add_argument('--map_in', '-mi', required=False,
                        help='Input file name for the old sov map. This should be the output of the last render. It '
                             'will be used to render areas where the influence has changed with stripes. If not '
                             'provided, the map will be rendered without stripes.')
    args = parser.parse_args()

    print("Loading data from database...")
    owners, systems, connections, sov_changes, regions = load_data_from_db(
        args.host, args.user, args.password, args.database)

    render(
        owners, systems, connections, sov_changes, regions,
        path_map_in=args.map_in,
        path_map_out=args.map_out,
        img_out=args.output,
        text=args.text
    )


def render(
        owners: list[dict],
        systems: list[dict],
        connections: list[tuple[int, int]],
        sov_changes: list[dict],
        regions: dict[int, dict],
        path_map_in: str | None = None,
        path_map_out: str | None = None,
        img_out: str = "influence.png",
        text: list[str] | None = None,
):
    """
    Render the influence map.
    :param owners:       a list of owners, every owner is a dict with the keys
                         `id`, `color`, `name`, `npc`. `color` is nullable, `name` may be missing.
    :param systems:      a list of systems, every system is a dict with the keys
                         `id`, `name`, `constellation_id`, `region_id`, `x`, `y`, `z`, `has_station`, `sov_power`, `owner`.
                         `owner` may be missing.
    :param connections:  a list of connections, every connection is a tuple of two system ids.
    :param sov_changes:  a list of sov changes, every change is a dict with the keys `from`, `to`, `system`, `sov_power`.
    :param regions:      a dict of regions, every region is a dict with the keys `id`, `name`, `x`, `y`, `z`.
    :param path_map_in:  the path to the old map data, if available.
    :param path_map_out: the output path for the new map data.
    :param img_out:      the output path for the image.
    :param text:         the text to render in the top left corner. See the help str of the main function for details.
    :return:
    """
    import PIL
    from PIL import Image, ImageDraw, ImageFont

    try:
        base_font_b = ImageFont.truetype(r"C:\Windows\Fonts\VerdanaB.ttf")
        #base_font = ImageFont.truetype(r"C:\Windows\Fonts\Verdana.ttf")
    except OSError:
        print("Verdana font not found, using default font.")
        base_font_b = None
        #base_font = None
    try:
        font_arial = ImageFont.truetype("arial.ttf")
        font_arialb = ImageFont.truetype("arialbd.ttf")
        if base_font_b is None:
            base_font_b = font_arialb
    except OSError:
        print("Arial font not found, using default font.")
        font_arial = None
        font_arialb = None
    if font_arial is None:
        font_arial = ImageFont.load_default()
    if font_arialb is None:
        font_arialb = font_arial
    if base_font_b is None:
        base_font_b = font_arialb

    print("Preparing map...")
    sov_map = SovMap()
    sov_map.update_size()
    sov_map.load_data(owners, systems, connections, regions=regions.values())
    if path_map_in:
        sov_map.load_old_owner_data(path_map_in)

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
    if path_map_out:
        sov_map.save_owner_data(path_map_out, compress=True)

    print("Calculating labels...")
    start = datetime.now()
    sov_map.calculate_labels()
    diff = datetime.now() - start
    print(f"Label calculation took {diff.total_seconds():.4f} seconds.")

    print("Rendering overlay...")
    sov_layer = sov_map.get_image().as_pil_image()
    sys_layer = PIL.Image.new("RGBA", sov_layer.size, (0, 0, 0, 0))
    bg_layer = PIL.Image.new("RGBA", sov_layer.size, (0, 0, 0, 255))
    label_layer = PIL.Image.new("RGBA", bg_layer.size, (0, 0, 0, 0))
    legend_layer = PIL.Image.new("RGBA", bg_layer.size, (0, 0, 0, 0))
    sys_draw = ImageDraw.Draw(sys_layer)
    sov_map.draw_systems(sys_draw)
    sov_map.draw_region_labels(sys_draw, font=font_arial.font_variant(size=10))
    sov_map.draw_owner_labels(ImageDraw.Draw(label_layer), base_font=base_font_b)

    # Draw legend
    draw = ImageDraw.Draw(legend_layer)

    font_header = font_arialb.font_variant(size=16)
    font_normal = font_arial.font_variant(size=16)

    if not text:
        lines = [
            (font_header, "EVE Echoes Null-Sec Player Influence Map"),
            (font_normal, "Generated by <NAME>"),
            (font_normal, "Using github.com/Blaumeise03/bluemap"),
            (font_normal, "Powered by <URL>"),
            (font_normal, "Using sovereignty data for <DATE>"),
        ]
    else:
        lines = []
        for line in text:
            if not line:
                lines.append(None)
            elif len(line) == 1:
                lines.append((font_normal, line[0]))
            else:
                lines.append((font_header, line[1]))

    y = 17
    for line in lines:
        if line is not None:
            draw.text(
                xy=(4, y),
                text=line[1],
                font=line[0],
                fill=(64, 64, 64),
            )
        y += 18

    y += 18

    table = Table((64, 64, 64, 255), fixed_col_widths=[100, 100, 50, 80])
    table.font = font_arial.font_variant(size=10)
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
                regions[system.region_id]['name']
            ],
            [
                from_owner.color if from_owner else (0, 0, 0, 255),
                to_owner.color if to_owner else (0, 0, 0, 255),
                (200, 200, 255, 255), (200, 200, 200, 255)],
            bg_color=(0, 0, 0x40, 255) if change['sov_power'] >= 6.0 else None
        )
    table.render(draw, (10, y))

    combined = PIL.Image.alpha_composite(sov_layer, sys_layer)
    combined = PIL.Image.alpha_composite(combined, label_layer)
    combined = PIL.Image.alpha_composite(combined, legend_layer)
    combined = PIL.Image.alpha_composite(bg_layer, combined)

    print("Saving map...")
    combined.save(img_out)
    print("Done.")


if __name__ == "__main__":
    main()
