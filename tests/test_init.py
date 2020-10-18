"""
Test module for . . .
"""
# Standard library imports
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)
import logging
import pathlib
from os.path import abspath, dirname, join, realpath
from sys import path

# Third party imports
import pytest


# Local imports
import pypiserver

logger = logging.getLogger(__name__)

TEST_DIR = pathlib.Path(__file__).parent
HTPASS_FILE = TEST_DIR / "htpasswd.a.a"


# TODO: make these tests meaningful
@pytest.mark.parametrize(
    "conf_options",
    [
        {},
        {"root": "~/stable_packages"},
        {
            "root": "~/unstable_packages",
            "authenticated": "upload",
            "passwords": str(HTPASS_FILE),
        },
        # Verify that the strip parser works properly.
        {"authenticated": str("upload")},
    ],
)
def test_paste_app_factory(conf_options):
    """Test the paste_app_factory method"""
    # monkeypatch.setattr(
    #     "pypiserver.core.configure", lambda **x: (x, [x.keys()])
    # )
    pypiserver.paste_app_factory({}, **conf_options)


def test_app_factory():
    # monkeypatch.setattr(
    #     "pypiserver.core.configure", lambda **x: (x, [x.keys()])
    # )
    assert pypiserver.app() is not pypiserver.app()
