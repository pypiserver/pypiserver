#! /usr/bin/env py.test

import pytest
import re
from pypiserver import version as my_ver

@pytest.fixture()
def readme():
    return open('README.rst', 'rt').read()

def test_READMEversion(readme):
    m = re.compile(r'^\s*:Version:\s*(.+)\s*$', re.MULTILINE).search(readme)
    assert m, "Could not find version on README!"
    assert m.group(1) == my_ver, 'Updaed version(%s) on README!' % m.group(1) 
