"""A simple package to use to generate a wheel.

This is not called by tests directly, but is the source of the
simple_pkg wheel file used in integration tests.
"""

from setuptools import setup

setup(
    name='simple_pkg',
    description='A simple package',
    version='0.0.0',
    options={'bdist_wheel': {'universal': True}}
)
