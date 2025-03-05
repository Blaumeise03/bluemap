import platform

from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension(
        name="bluemap._map",
        sources=[
            "bluemap/_map.pyx",
            "cpp/Image.cpp",
            "cpp/Map.cpp",
            "cpp/PyWrapper.cpp",
        ],
        include_dirs=["cpp"],
        language="c++",
        extra_compile_args=["-std=c++17" if platform.system() != "Windows" else "/std:c++17"],
        define_macros=[("EVE_MAPPER_PYTHON", "1")]
    ),
    Extension(
        name="bluemap.stream",
        sources=[
            "bluemap/stream.pyx",
        ]
    )
]

setup(
    name="bluemap",
    version="1.0.0a1.dev1",
    packages=["bluemap"],
    ext_modules=cythonize(extensions, annotate=True),
    entry_points={
        'console_scripts': [
            'bluemap = bluemap.main:main',
        ],
    },
    build_requires=["setuptools", "Cython"]
)