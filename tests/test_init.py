"""Test module for pypiserver.__init__"""
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
import logging

import pypiserver

logger = logging.getLogger(__name__)


def test_app_factory(monkeypatch, tmpdir):
    """Test creating an app."""
    conf = pypiserver.config.Config(
        parser_type='pypi-server'
    ).get_parser().parse_args([str(tmpdir)])
    assert pypiserver.app(conf) is not pypiserver.app(conf)
