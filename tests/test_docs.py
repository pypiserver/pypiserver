#! /usr/bin/env py.test
from pathlib import Path

import pytest
import re
from pypiserver import version as my_ver


@pytest.fixture()
def readme():
    return Path(__file__).parents[1].joinpath("README.rst").read_text()


def test_READMEversion(readme):
    m = re.compile(r"^\s*:Version:\s*(.+)\s*$", re.MULTILINE).search(readme)
    assert m, "Could not find version on README!"
    assert m.group(1) == my_ver, f"Updated version({m.group(1)}) on README!"
