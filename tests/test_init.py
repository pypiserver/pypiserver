"""
Test module for app initialization
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
    pypiserver.paste_app_factory({}, **conf_options)


def test_app_factory():
    assert pypiserver.app() is not pypiserver.app()
