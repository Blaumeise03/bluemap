bluemap - Influence map generator
=================================
Bluemap is an influence map generator for games like Eve Online/Echoes. It is
based on the algorithm from Paladin Vent (which was continued by Verite Rendition),
but was written from scratch in C++ and Cython. It is designed to be faster and easier
to use. While the algorithm for the influence layer itself stayed the same and should
produce identical images, the other features of the map (like system connections, legend, etc.)
are slightly different. But overall, the map should look very similar to the original.

<!-- TOC -->
* [Overview](#overview)
* [Installation](#installation)
* [Usage (CLI)](#usage-cli)
* [Usage (Library)](#usage-library)
  * [Rendering](#rendering)
  * [Tables](#tables)
* [Building](#building)
  * [Python](#python)
  * [Standalone](#standalone)
* [Credits](#credits)
<!-- TOC -->

> This project is still work in progress. The API might change until the version 1.0.0 is released. If you decide to
> already use it, please make sure to pin the version in your requirements.txt file. Until version 1.0.0 is released,
> minor versions might contain breaking changes. I will try to keep the changes as minimal as possible, but I cannot
> guarantee that there will be no breaking changes.

> If you find a bug or have a feature request, please open an issue on GitHub.

# Overview
As stated before, this project is implemented in C++ and Cython. The C++ part is responsible
for the rendering of the influence layer, and the calculation of the owner label positions.
All other parts are implemented in Cython and Python.

The C++ library does work in general standalone, but except for a testing tool that requires
a specific file format as input, there is no real way to use it directly. So you would have
to write your own wrapper around it, which loads the data from some source.

![Example Map](https://github.com/user-attachments/assets/76c4d56f-23e2-44c6-90d6-0af466e7c855)


# Installation
PyPi has precompiled wheels for Windows (64bit), Linux and macOS (min version 14.0, untested). 32bit Windows is 
supported but not automated. PyPi may or may not have a precompiled wheel for 32bit Windows.

We support Python 3.12 and higher (atm 3.12 and 3.13 on PyPi)

The precompiled package can be installed via pip. There are multiple variations that can be installed via pip:

| Name               | Map | Tables | MySQL DB |
|--------------------|-----|--------|----------|
| `bluemap[minimal]` | ✅   | ❌      | ❌        |
| `bluemap[table]`   | ✅   | ✅      | ❌        |
| `bluemap[CLI]`     | ✅   | ✅      | ✅        |

e.g. to install the full version, you can use the following command:
```sh
pip install bluemap[CLI]
```

- Map: The module for rendering the influence map
- Tables: The module for rendering tables (depends on Pillow)
- MySQL DB: The module for loading data from a MySQL database (depends on pymysql)

Also note all functionality is available in the `bluemap` package. The extras are only for the convenience of the
installation. You can also install the base version and add the dependencies manually.

# Usage (CLI)
The CLI supports rendering of maps with data from a mysql database. The program will create all required tables
on the first run. However, you do have to populate the tables yourself. You can find the static data for Eve Online on
the [UniWIKI](https://wiki.eveuniversity.org/Static_Data_Export). For the sovereignty data, you need to use the ESI API.

| Arg                    | Description                                     |
|------------------------|-------------------------------------------------|
| `--help,-h`            | Show the help message                           |
| `--host HOST`          | The host of the db                              |
| `--user USER`          | The user for the db                             |
| `--password PASSWORD`  | The password for the db (empty for no password) |
| `--database DATABASE`  | The database to use                             |
| `--text [header] TEXT` | Extra text to render (see below)                |
| `--output,-o OUTPUT`   | The output file for the image                   |
| `--map_out,-mo PATH`   | The output file for the map data                |
| `--map_in,-mi PATH`    | The input file for the old map data             |

The database args are all required, the other ones are optional. `map_in` and `map_out` are used for the rendering of
changed influence areas. If the old map is provided, in areas where the influence changed, the old influence will be 
rendered as diagonal lines. These files in principle simply store the id of the owner for every pixel. Please refer
to the implementation for the exact format.

The `text` argument is used to render additional text in the top left corner. This argument may be repeated multiple
times for multiple lines of text. There are three ways to use this

1. `--text "Some text"`: This will render the text in the default font
2. `--text header "Some text"`: This will render the text in the header font (bold)
3. `--text`: This will render an empty line (but an empty string would also work)

(all three ways can be chained for multiple lines)

Example usage:
```shell
python -m bluemap.main \
       --host localhost \
       --user root \
       --password "" \
       --database evemap \
       -o influence.png \
       -mi sovchange_2025-02-16.dat \
       -mo sovchange_2025-02-23.dat \
       --text header "Influence Map" \
       --text \
       --text "Generated by Blaumeise03"
```

# Usage (Library)
The library is very simple to use. You can find an example inside the [main.py](bluemap/main.py) file. The main class
is the `SovMap` class. This does all the heavy lifting. The `load_data` method is used to load the data into the map.

Please note that the API is subject to change until version 1.0.0 is released. I recommend pinning the version in your
requirements.txt file and manually update it.

```python
from bluemap import SovMap

sov_map = SovMap()

sov_map.load_data(
    owners=[{
        'id': 10001,
        'color': (0, 255, 0),
        'name': 'OwnerA',
        'npc': False,
    }],
    systems=[
        {
            'id': 20001, 'name': 'Jita',
            'constellation_id': 30001, 'region_id': 40001,
            'x': -129064e12, 'y': 60755e12, 'z': -117469e12,
            'has_station': True,
            'sov_power': 6.0,
            'owner': 10001,
        }, {'id': 20002, 'name': ...}
    ],
    connections=[
        (20001, 20002),
    ],
    regions=[{'id': 40001, 'name': 'The Forge',
              'x': -96420e12, 'y': 64027e12, 'z': -112539e12},
             ],
    filter_outside=True, # Will skip all systems outside the map
)
```
For the rendering, please refer to the `render` method inside the [main.py](bluemap/main.py). You can see the usage
with documentation there.

## Rendering
Some more special methods. First of all, the rendering is implemented in C++ and does not interact with Python. 
Therefore, it can be used with Python's multithreading. In general, all methods are thread safe. But any modifications to
the map are blocked as long as any thread is rendering. The rendering will split the map into columns, every thread
will render one column. There is a default implementation inside [_map.pyx](bluemap/_map.pyx):
```python
from bluemap import SovMap, ColumnWorker
sov_map = SovMap()
if not sov_map.calculated:
    sov_map.calculate_influence()
from concurrent.futures.thread import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=16) as pool:
    workers = sov_map.create_workers(16)
    pool.map(ColumnWorker.render, workers)
```
But please make sure, two ColumnWorkers who overlap are not thread safe. The `create_workers` method will generate
disjoint workers. But if you call the method multiple times, you have to make sure the workers are disjointed. See the
source code of the `SovMap.render` functions for more information.

## Tables
The module `bluemap.table` contains classed for rendering of tables. This requires the `Pillow` package. Please refer
to the example inside the [main.py](bluemap/main.py) file on how to use it.


# Building
## Python
On windows, this project requires the MSVC compiler. The library requires at least C++17, if you use a different 
compiler on windows, you will have to modify the `extra_compile_args` inside the [setup.py](setup.py) file.

Also, this project requires Python 3.12 or higher. I have not tested it with lower versions, but the C++ code gets
compiled against CPython and uses features from the C-API that require Python 3.12. That being said, this is technically
speaking not required. You could disable the C-API usage, but at the moment, you would have to remove the functions
from the Cython code that depend on the C-API.

Compiling can either happen via
```sh
python -m build
```
or, if you want to build it in-place
```sh
python setup.py build_ext --inplace
```
this will also generate `.html` files for an analysis of the Cython code.

## Standalone
This project has a small CMakelists.txt file that can be used to compile the C++ code as a standalone executable. It 
does download std_image_write from GitHub to write the png image. However, as I have mentioned, the C++ code has no
nice way to load the data. Refer to `Map::load_data` inside the [Map.cpp](cpp/Map.cpp) file for the required format.


# Credits
The original algorithm was created by Paladin Vent and continued by Verite Rendition. Verite's version can be found at
[https://www.verite.space/](https://www.verite.space/). I do not know if Paladin Vent has a website (feel free to
contact me to add it here). The original algorithm was written in Java and can be found on Verite's website.
