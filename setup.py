import platform

from Cython.Build import cythonize
from setuptools import setup, Extension

GEN_COVERAGE = False


macros = [("EVE_MAPPER_PYTHON", "1")]
if GEN_COVERAGE:
    macros.append(("CYTHON_TRACE_NOGIL", "1"))

extensions = [
    Extension(
        name="bluemap._map",
        sources=[
            "bluemap/_map.pyx",
            "cpp/Image.cpp",
            "cpp/Map.cpp",
            "cpp/PyWrapper.cpp",
            "cpp/traceback_wrapper.cpp",
        ],
        include_dirs=["cpp"],
        language="c++",
        extra_compile_args=["-std=c++17" if platform.system() != "Windows" else "/std:c++17"],
        define_macros=macros,
    ),
    Extension(
        name="bluemap.stream",
        sources=[
            "bluemap/stream.pyx",
        ],
        define_macros=macros,
    )
]

setup(
    name="bluemap",
    version="1.0.0a1.dev1",
    packages=["bluemap"],
    ext_modules=cythonize(
        extensions,
        annotate=True,
        compiler_directives={
            'profile': True if GEN_COVERAGE else False,
            'linetrace': True if GEN_COVERAGE else False,
        }
    ),
    entry_points={
    },
    build_requires=["setuptools", "Cython"],
)