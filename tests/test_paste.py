"""Test the paste-compatible app factory."""

import pytest

from pypiserver import paste
from pypiserver.core import load_plugins


def configure_fake(config):
    """Fake for the configure() function."""
    config.plugins = load_plugins()
    return config, []


@pytest.mark.parametrize('conf_options', [
    {},
    {'root': '~/stable_packages'},
    {'root': '~/unstable_packages', 'authenticated': 'upload',
     'passwords': '~/htpasswd'},
    # Verify that the strip parser works properly.
    {'authenticated': str('upload')},
])
def test_paste_app_factory(conf_options, monkeypatch):
    """Test the paste_app_factory method."""
    monkeypatch.setattr('pypiserver.core.configure', configure_fake)
    paste.paste_app_factory({}, **conf_options)
