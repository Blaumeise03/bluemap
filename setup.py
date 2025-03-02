from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension(
        name="bluemap.wrapper",
        sources=[
            "bluemap/wrapper.pyx",
            "cpp/Image.cpp",
            "cpp/Map.cpp"
        ],
        include_dirs=["cpp"],
        language="c++",
        extra_compile_args=["-std=c++17", "/std:c++17"]
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