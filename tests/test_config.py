"""Test the ArgumentParser and associated functions."""

import logging
from os import getcwd
from os.path import expanduser
from platform import system

import pytest

from pypiserver import config


@pytest.fixture()
def parser():
    """Return a fresh parser."""
    return config.get_parser()


class StubAction:
    """Quick stub for argparse actions."""

    def __init__(self, option_strings):
        """Set stub attributes."""
        self.help = 'help'
        self.default = 'default'
        self.nargs = '*'
        self.option_strings = option_strings


@pytest.mark.parametrize('options, expected_help', (
    (['--foo'], 'help (default: %(default)s)'),
    (['cmd'], 'help (default: %(default)s)'),
    (['--disable-fallback'], 'help (default: False)'),
))
def test_argument_formatter(options, expected_help):
    """Test the custom formatter class.

    In general, it should always just return help (default: %(default)s)
    except when the option_strings contain --disable-fallback, our special
    case.
    """
    action = StubAction(options)
    assert config.ArgumentFormatter('prog')._get_help_string(action) == (
        expected_help
    )


@pytest.mark.parametrize('arg, exp', (
    ('update download list', ['update', 'download', 'list']),
    ('update, download, list', ['update', 'download', 'list']),
    ('update', ['update']),
    ('update,', ['update']),
    ('update, ', ['update']),
    ('update , ', ['update']),
    ('update ', ['update']),
    ('update , download', ['update', 'download']),
    ('.', []),
))
def test_auth_parse_success(arg, exp):
    """Test parsing auth strings from the commandline."""
    assert config.auth_parse(arg) == exp


def test_auth_parse_disallowed_item():
    """Test that including a non-whitelisted action throws."""
    with pytest.raises(ValueError):
        config.auth_parse('download update foo')


def test_roots_parse_abspath():
    """Test the parsing of root directories returns absolute paths."""
    assert config.roots_parse(['./foo']) == ['{}/foo'.format(getcwd())]


def test_roots_parse_home():
    """Test that parsing of root directories expands the user home."""
    assert config.roots_parse(['~/foo']) == ([expanduser('~/foo')])


def test_roots_parse_both():
    """Test that root directories are both expanded and absolute-ed."""
    assert config.roots_parse(['~/foo/..']) == [expanduser('~')]


@pytest.mark.parametrize('verbosity, exp', (
    (0, logging.WARNING),
    (1, logging.INFO),
    (2, logging.DEBUG),
    (3, logging.NOTSET),
    (5, logging.NOTSET),
    (100000, logging.NOTSET),
    (-1, logging.NOTSET),
))
def test_verbosity_parse(verbosity, exp):
    """Test converting a number of -v's into a log level."""
    assert config.verbosity_parse(verbosity) == exp


class TestParser:
    """Tests for the parser itself."""

    def test_version_exits(self, parser):
        """Test that asking for the version exits the program."""
        with pytest.raises(SystemExit):
            parser.parse_args(['--version'])

    @pytest.mark.parametrize('args, exp', (
        ([], logging.WARNING),
        (['-v'], logging.INFO),
        (['-vv'], logging.DEBUG),
        (['-vvv'], logging.NOTSET),
        (['-vvvvvvv'], logging.NOTSET),
        (['-v', '--verbose'], logging.DEBUG),
        (['--verbose', '--verbose'], logging.DEBUG),
        (['-v', '-v'], logging.DEBUG),
    ))
    def test_specifying_verbosity(self, parser, args, exp):
        """Test that verbosity is set correctly for -v arguments."""
        assert parser.parse_args(args).verbosity == exp

    @pytest.mark.parametrize('args, exp', (
        ([], list(map(expanduser, config._Defaults.roots))),
        (['/foo'], ['/foo']),
        (['/foo', '~/bar'], ['/foo', expanduser('~/bar')]),
    ))
    def test_roots(self, parser, args, exp):
        """Test specifying package roots."""
        assert parser.parse_args(args).roots == exp

    @pytest.mark.parametrize('args, exp', (
        ([], config._Defaults.host),
        (['-i', '1.1.1.1'], '1.1.1.1'),
        (['--interface', '1.1.1.1'], '1.1.1.1'),
    ))
    def test_interface(self, parser, args, exp):
        """Test specifying package roots."""
        assert parser.parse_args(args).host == exp

    @pytest.mark.parametrize('args, exp', (
        ([], config._Defaults.port),
        (['-p', '999'], 999),
        (['--port', '1234'], 1234),
    ))
    def test_port(self, parser, args, exp):
        """Test specifying package roots."""
        assert parser.parse_args(args).port == exp

    @pytest.mark.parametrize('args, exp', (
        ([], False),
        (['-o'], True),
        (['--overwrite'], True),
    ))
    def test_overwrite(self, parser, args, exp):
        """Test specifying package roots."""
        assert parser.parse_args(args).overwrite == exp

    @pytest.mark.parametrize('args, exp', (
        ([], config._Defaults.fallback_url),
        (['--fallback-url', 'http://www.google.com'], 'http://www.google.com'),
    ))
    def test_fallback_url(self, parser, args, exp):
        """Test specifying package roots."""
        assert parser.parse_args(args).fallback_url == exp
