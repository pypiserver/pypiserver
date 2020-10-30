"""
Test module for app initialization
"""
# Standard library imports
import logging
import pathlib
import typing as t

# Third party imports
import pytest


# Local imports
import pypiserver

logger = logging.getLogger(__name__)

TEST_DIR = pathlib.Path(__file__).parent
HTPASS_FILE = TEST_DIR / "htpasswd.a.a"
WELCOME_FILE = TEST_DIR / "sample_msg.html"


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
def test_paste_app_factory(conf_options: dict) -> None:
    """Test the paste_app_factory method"""
    pypiserver.paste_app_factory({}, **conf_options)  # type: ignore


def test_app_factory() -> None:
    assert pypiserver.app() is not pypiserver.app()


@pytest.mark.parametrize(
    "incoming, updated",
    (
        (
            {"authenticated": []},
            {"authenticate": []},
        ),
        (
            {"passwords": "./foo"},
            {"password_file": "./foo"},
        ),
        (
            {"root": str(TEST_DIR)},
            {"roots": [TEST_DIR.expanduser().resolve()]},
        ),
        (
            {"root": [str(TEST_DIR), str(TEST_DIR)]},
            {
                "roots": [
                    TEST_DIR.expanduser().resolve(),
                    TEST_DIR.expanduser().resolve(),
                ]
            },
        ),
        (
            {"redirect_to_fallback": False},
            {"disable_fallback": True},
        ),
        (
            {"server": "auto"},
            {"server_method": "auto"},
        ),
        (
            {"welcome_file": str(WELCOME_FILE.resolve())},
            {"welcome_msg": WELCOME_FILE.read_text()},
        ),
    ),
)
def test_backwards_compat_kwargs_conversion(
    incoming: t.Dict[str, t.Any], updated: t.Dict[str, t.Any]
) -> None:
    """Test converting legacy kwargs to modern ones."""
    assert pypiserver.backwards_compat_kwargs(incoming) == updated


@pytest.mark.parametrize(
    "kwargs",
    (
        {"redirect_to_fallback": False, "disable_fallback": False},
        {"disable_fallback": False, "redirect_to_fallback": False},
    ),
)
def test_backwards_compat_kwargs_duplicate_check(
    kwargs: t.Dict[str, t.Any]
) -> None:
    """Duplicate legacy and modern kwargs cause an error."""
    with pytest.raises(ValueError) as err:
        pypiserver.backwards_compat_kwargs(kwargs)
    assert "('redirect_to_fallback', 'disable_fallback')" in str(err.value)
