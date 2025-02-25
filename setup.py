from setuptools import setup

setup(
    name="bluemap",
    version="1.0.0",
    packages=["bluemap"],
    entry_points={
        'console_scripts': [
            'bluemap = bluemap.main:main',
        ],
    },
)