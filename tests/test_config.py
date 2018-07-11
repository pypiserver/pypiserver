"""Test the ArgumentParser and associated functions."""

import argparse
import logging
from os import getcwd
from os.path import exists, expanduser

try:
    from unittest.mock import Mock
except ImportError:  # py2
    from mock import Mock

import pytest

from pypiserver import config
from pypiserver import const


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
    assert config._HelpFormatter('prog')._get_help_string(action) == (
        expected_help
    )


class TestCustomParsers(object):

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
    def test_auth_parse_success(self, arg, exp):
        """Test parsing auth strings from the commandline."""
        assert config._CustomParsers.auth(arg) == exp

    def test_auth_parse_disallowed_item(self):
        """Test that including a non-whitelisted action throws."""
        with pytest.raises(ValueError):
            config._CustomParsers.auth('download update foo')

    def test_roots_parse_abspath(self):
        """Test the parsing of root directories returns absolute paths."""
        assert config._CustomParsers.roots(
            ['./foo']
        ) == ['{}/foo'.format(getcwd())]

    def test_roots_parse_home(self):
        """Test that parsing of root directories expands the user home."""
        assert config._CustomParsers.roots(
            ['~/foo']
        ) == ([expanduser('~/foo')])

    def test_roots_parse_both(self):
        """Test that root directories are both expanded and absolute-ed."""
        assert config._CustomParsers.roots(
            ['~/foo/..']
        ) == [expanduser('~')]

    @pytest.mark.parametrize('verbosity, exp', (
        (0, logging.WARNING),
        (1, logging.INFO),
        (2, logging.DEBUG),
        (3, logging.NOTSET),
        (5, logging.NOTSET),
        (100000, logging.NOTSET),
        (-1, logging.NOTSET),
    ))
    def test_verbosity_parse(self, verbosity, exp):
        """Test converting a number of -v's into a log level."""
        assert config._CustomParsers.verbosity(verbosity) == exp


class TestDeprecatedParser:
    """Tests for the deprecated parser."""

    @pytest.fixture()
    def parser(self):
        """Return a deprecated parser."""
        return config.ConfigFactory(parser_type='pypi-server').get_parser()

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
        """Test specifying a server interface."""
        assert parser.parse_args(args).host == exp

    @pytest.mark.parametrize('args, exp', (
        ([], config._Defaults.port),
        (['-p', '999'], 999),
        (['--port', '1234'], 1234),
    ))
    def test_port(self, parser, args, exp):
        """Test specifying a server port."""
        assert parser.parse_args(args).port == exp

    @pytest.mark.parametrize('args, exp', (
        ([], False),
        (['-o'], True),
        (['--overwrite'], True),
    ))
    def test_overwrite(self, parser, args, exp):
        """Test the overwrite flag."""
        assert parser.parse_args(args).overwrite == exp

    @pytest.mark.parametrize('args, exp', (
        ([], config._Defaults.fallback_url),
        (['--fallback-url', 'http://www.google.com'], 'http://www.google.com'),
    ))
    def test_fallback_url(self, parser, args, exp):
        """Test specifying a fallback URL."""
        assert parser.parse_args(args).fallback_url == exp

    @pytest.mark.parametrize('args, exp', (
        ([], config._Defaults.redirect_to_fallback),
        (['--disable-fallback'], not config._Defaults.redirect_to_fallback),
    ))
    def test_disable_fallback(self, parser, args, exp):
        """Test disabling the fallback."""
        assert parser.parse_args(args).redirect_to_fallback is exp

    @pytest.mark.parametrize('args, exp', (
        ([], config._Defaults.server),
        (['--server', 'paste'], 'paste'),
    ))
    def test_specify_server(self, parser, args, exp):
        """Test specifying a server."""
        assert parser.parse_args(args).server == exp

    def test_specify_server_bad_arg(self, parser):
        """Test specifying an unsupported server."""
        with pytest.raises(SystemExit):
            parser.parse_args(['--server', 'foobar'])

    @pytest.mark.parametrize('args, exp', (
        ([], config._Defaults.hash_algo),
        (['--hash-algo', 'sha256'], 'sha256'),
        (['--hash-algo', 'no'], None),
        (['--hash-algo', 'false'], None),
        (['--hash-algo', '0'], None),
        (['--hash-algo', 'off'], None),
    ))
    def test_specify_hash_algo(self, parser, args, exp):
        """Test specifying a hash algorithm."""
        assert parser.parse_args(args).hash_algo == exp

    def test_bad_hash_algo(self, parser):
        """Test an unavailable hash algorithm."""
        with pytest.raises(SystemExit):
            parser.parse_args(['--hash-algo', 'foobar-loo'])

    @pytest.mark.parametrize('args, exp', (
        ([], None),
        (['--welcome', 'foo'], 'foo'),
    ))
    def test_specify_welcome_html(self, parser, args, exp):
        """Test specifying a welcome file."""
        welcome = parser.parse_args(args).welcome_file
        if exp is None:
            # Ensure the pkg_resources file path is returned correctly
            assert welcome.endswith('welcome.html')
            assert exists(welcome)
        else:
            assert parser.parse_args(args).welcome_file == exp

    def test_standalone_welcome(self, monkeypatch):
        """Test that the error raised in the standalone package is handled."""
        monkeypatch.setattr(
            config.pkg_resources,
            'resource_filename',
            Mock(side_effect=NotImplementedError)
        )
        assert config.ConfigFactory(
            parser_type='pypi-server'
        ).get_parser().parse_args([]).welcome_file == const.STANDALONE_WELCOME

    @pytest.mark.parametrize('args, exp', (
        ([], None),
        (['--cache-control', '12'], 12),
    ))
    def test_specify_cache_control(self, parser, args, exp):
        """Test specifying cache retention time."""
        assert parser.parse_args(args).cache_control == exp

    @pytest.mark.parametrize('args, exp', (
        ([], ['update']),
        (['-a', '.'], []),
        (['--authenticate', '.'], []),
        (['-a', 'update download'], ['update', 'download']),
        (['-a', 'update, download'], ['update', 'download']),
        (['-a', 'update,download'], ['update', 'download']),
    ))
    def test_specify_auth(self, parser, args, exp):
        """Test specifying cache retention time."""
        assert parser.parse_args(args).authenticate == exp

    @pytest.mark.parametrize('args, exp', (
        ([], None),
        (['-P', 'foo'], 'foo'),
        (['--passwords', 'foo'], 'foo'),
    ))
    def test_specify_password_file(self, parser, args, exp):
        """Test specifying cache retention time."""
        assert parser.parse_args(args).password_file == exp

    @pytest.mark.parametrize('attr, args, exp', (
        ('log_file', [], None),
        ('log_file', ['--log-file', 'foo'], 'foo'),
        ('log_frmt', [], config._Defaults.log_fmt),
        ('log_frmt', ['--log-frmt', 'foo'], 'foo'),
    ))
    def test_log_args(self, parser, attr, args, exp):
        """Test various log args."""
        assert getattr(parser.parse_args(args), attr) == exp

    @pytest.mark.parametrize('attr, args, exp', (
        ('log_req_frmt', [], config._Defaults.log_req_fmt),
        ('log_req_frmt', ['--log-req-frmt', 'foo'], 'foo'),
        ('log_res_frmt', [], config._Defaults.log_res_fmt),
        ('log_res_frmt', ['--log-res-frmt', 'foo'], 'foo'),
        ('log_err_frmt', [], config._Defaults.log_err_fmt),
        ('log_err_frmt', ['--log-err-frmt', 'foo'], 'foo'),
    ))
    def test_http_log_args(self, parser, attr, args, exp):
        """Test HTTP log args."""
        assert getattr(parser.parse_args(args), attr) == exp

    @pytest.mark.parametrize('args, exp', (
        ([], False),
        (['-U'], True),
        (['--update-packages'], True),
    ))
    def test_update_flag(self, parser, args, exp):
        """Test specifying the update flag."""
        assert parser.parse_args(args).update_packages is exp

    @pytest.mark.parametrize('args, exp', (
        ([], False),
        (['-x'], True),
        (['--execute'], True),
    ))
    def test_execute_flag(self, parser, args, exp):
        """Test specifying the execute flag."""
        assert parser.parse_args(args).execute is exp

    @pytest.mark.parametrize('args, exp', (
        ([], False),
        (['-u'], True),
        (['--unstable'], True),
    ))
    def test_unstable_flag(self, parser, args, exp):
        """Test specifying the execute flag."""
        assert parser.parse_args(args).unstable is exp

    @pytest.mark.parametrize('args, exp', (
        ([], None),
        (['--download-directory', 'foo'], 'foo'),
    ))
    def test_download_directory(self, parser, args, exp):
        """Test specifying the execute flag."""
        assert parser.parse_args(args).download_directory is exp


class TestParser:
    """Tests for the parser."""

    @pytest.fixture()
    def parser(self):
        """Return a deprecated parser."""
        return config.ConfigFactory().get_parser()

    # **********************************************************************
    # Root Command
    # **********************************************************************

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
    def test_specifying_verbosity_run(self, parser, args, exp):
        """Test that verbosity is set correctly for -v arguments."""
        args.append('run')
        assert parser.parse_args(args).verbosity == exp

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
    def test_specifying_verbosity_update(self, parser, args, exp):
        """Test that verbosity is set correctly for -v arguments."""
        args.append('update')
        assert parser.parse_args(args).verbosity == exp

    @pytest.mark.parametrize('attr, args, exp', (
        ('log_file', [], None),
        ('log_file', ['--log-file', 'foo'], 'foo'),
        ('log_frmt', [], config._Defaults.log_fmt),
        ('log_frmt', ['--log-frmt', 'foo'], 'foo'),
    ))
    def test_log_args_run(self, parser, attr, args, exp):
        """Test various log args."""
        args.append('run')
        assert getattr(parser.parse_args(args), attr) == exp

    @pytest.mark.parametrize('attr, args, exp', (
        ('log_file', [], None),
        ('log_file', ['--log-file', 'foo'], 'foo'),
        ('log_frmt', [], config._Defaults.log_fmt),
        ('log_frmt', ['--log-frmt', 'foo'], 'foo'),
    ))
    def test_log_args_update(self, parser, attr, args, exp):
        """Test various log args."""
        args.append('update')
        assert getattr(parser.parse_args(args), attr) == exp

    # **********************************************************************
    # Run Subcommand
    # **********************************************************************

    def test_raw_run_command(self, parser):
        """Ensure the command name is stored."""
        assert parser.parse_args(['run']).command == 'run'

    @pytest.mark.parametrize('args, exp', (
        ([], list(map(expanduser, config._Defaults.roots))),
        (['/foo'], ['/foo']),
        (['/foo', '~/bar'], ['/foo', expanduser('~/bar')]),
    ))
    def test_roots(self, parser, args, exp):
        """Test specifying package roots."""
        args.insert(0, 'run')
        assert parser.parse_args(args).roots == exp

    @pytest.mark.parametrize('args, exp', (
        ([], config._Defaults.host),
        (['-i', '1.1.1.1'], '1.1.1.1'),
        (['--interface', '1.1.1.1'], '1.1.1.1'),
    ))
    def test_interface(self, parser, args, exp):
        """Test specifying a server interface."""
        args.insert(0, 'run')
        assert parser.parse_args(args).host == exp

    @pytest.mark.parametrize('args, exp', (
        ([], config._Defaults.port),
        (['-p', '999'], 999),
        (['--port', '1234'], 1234),
    ))
    def test_port(self, parser, args, exp):
        """Test specifying a server port."""
        args.insert(0, 'run')
        assert parser.parse_args(args).port == exp

    @pytest.mark.parametrize('args, exp', (
        ([], False),
        (['-o'], True),
        (['--overwrite'], True),
    ))
    def test_overwrite(self, parser, args, exp):
        """Test the overwrite flag."""
        args.insert(0, 'run')
        assert parser.parse_args(args).overwrite == exp

    @pytest.mark.parametrize('args, exp', (
        ([], config._Defaults.fallback_url),
        (['--fallback-url', 'http://www.google.com'], 'http://www.google.com'),
    ))
    def test_fallback_url(self, parser, args, exp):
        """Test specifying a fallback URL."""
        args.insert(0, 'run')
        assert parser.parse_args(args).fallback_url == exp

    @pytest.mark.parametrize('args, exp', (
        ([], config._Defaults.redirect_to_fallback),
        (['--disable-fallback'], not config._Defaults.redirect_to_fallback),
    ))
    def test_disable_fallback(self, parser, args, exp):
        """Test disabling the fallback."""
        args.insert(0, 'run')
        assert parser.parse_args(args).redirect_to_fallback is exp

    @pytest.mark.parametrize('args, exp', (
        ([], config._Defaults.server),
        (['--server', 'paste'], 'paste'),
    ))
    def test_specify_server(self, parser, args, exp):
        """Test specifying a server."""
        args.insert(0, 'run')
        assert parser.parse_args(args).server == exp

    def test_specify_server_bad_arg(self, parser):
        """Test specifying an unsupported server."""
        with pytest.raises(SystemExit):
            parser.parse_args(['run', '--server', 'foobar'])

    @pytest.mark.parametrize('args, exp', (
        ([], config._Defaults.hash_algo),
        (['--hash-algo', 'sha256'], 'sha256'),
        (['--hash-algo', 'no'], None),
        (['--hash-algo', 'false'], None),
        (['--hash-algo', '0'], None),
        (['--hash-algo', 'off'], None),
    ))
    def test_specify_hash_algo(self, parser, args, exp):
        """Test specifying a hash algorithm."""
        args.insert(0, 'run')
        assert parser.parse_args(args).hash_algo == exp

    def test_bad_hash_algo(self, parser):
        """Test an unavailable hash algorithm."""
        with pytest.raises(SystemExit):
            parser.parse_args(['run', '--hash-algo', 'foobar-loo'])

    @pytest.mark.parametrize('args, exp', (
        ([], None),
        (['--welcome', 'foo'], 'foo'),
    ))
    def test_specify_welcome_html(self, parser, args, exp):
        """Test specifying a welcome file."""
        args.insert(0, 'run')
        welcome = parser.parse_args(args).welcome_file
        if exp is None:
            # Ensure the pkg_resources file path is returned correctly
            assert welcome.endswith('welcome.html')
            assert exists(welcome)
        else:
            assert parser.parse_args(args).welcome_file == exp

    def test_standalone_welcome(self, monkeypatch):
        """Test that the error raised in the standalone package is handled."""
        monkeypatch.setattr(
            config.pkg_resources,
            'resource_filename',
            Mock(side_effect=NotImplementedError)
        )
        assert config.ConfigFactory().get_parser().parse_args(
            ['run']
        ).welcome_file == const.STANDALONE_WELCOME

    @pytest.mark.parametrize('args, exp', (
        ([], None),
        (['--cache-control', '12'], 12),
    ))
    def test_specify_cache_control(self, parser, args, exp):
        """Test specifying cache retention time."""
        args.insert(0, 'run')
        assert parser.parse_args(args).cache_control == exp

    @pytest.mark.parametrize('args, exp', (
        ([], ['update']),
        (['-a', '.'], []),
        (['--authenticate', '.'], []),
        (['-a', 'update download'], ['update', 'download']),
        (['-a', 'update, download'], ['update', 'download']),
        (['-a', 'update,download'], ['update', 'download']),
    ))
    def test_specify_auth(self, parser, args, exp):
        """Test specifying authed actions."""
        args.insert(0, 'run')
        assert parser.parse_args(args).authenticate == exp

    @pytest.mark.parametrize('args, exp', (
        ([], None),
        (['-P', 'foo'], 'foo'),
        (['--passwords', 'foo'], 'foo'),
    ))
    def test_specify_password_file(self, parser, args, exp):
        """Test specifying a password file."""
        args.insert(0, 'run')
        assert parser.parse_args(args).password_file == exp

    @pytest.mark.parametrize('attr, args, exp', (
        ('log_req_frmt', [], config._Defaults.log_req_fmt),
        ('log_req_frmt', ['--log-req-frmt', 'foo'], 'foo'),
        ('log_res_frmt', [], config._Defaults.log_res_fmt),
        ('log_res_frmt', ['--log-res-frmt', 'foo'], 'foo'),
        ('log_err_frmt', [], config._Defaults.log_err_fmt),
        ('log_err_frmt', ['--log-err-frmt', 'foo'], 'foo'),
    ))
    def test_http_log_args(self, parser, attr, args, exp):
        """Test HTTP log args."""
        args.insert(0, 'run')
        assert getattr(parser.parse_args(args), attr) == exp

    # **********************************************************************
    # Update Subcommand
    # **********************************************************************

    def test_raw_update(self, parser):
        """Test that the update subcommand is stored properly."""
        assert parser.parse_args(['update']).command == 'update'

    @pytest.mark.parametrize('args, exp', (
        ([], list(map(expanduser, config._Defaults.roots))),
        (['/foo'], ['/foo']),
        (['/foo', '~/bar'], ['/foo', expanduser('~/bar')]),
    ))
    def test_update_roots(self, parser, args, exp):
        """Test specifying package roots."""
        args.insert(0, 'update')
        assert parser.parse_args(args).roots == exp

    @pytest.mark.parametrize('args, exp', (
        ([], False),
        (['-x'], True),
        (['--execute'], True),
    ))
    def test_execute_flag(self, parser, args, exp):
        """Test specifying the execute flag."""
        args.insert(0, 'update')
        assert parser.parse_args(args).execute is exp

    @pytest.mark.parametrize('args, exp', (
        ([], False),
        (['--pre'], True),
    ))
    def test_prerelease_flag(self, parser, args, exp):
        """Test specifying the execute flag."""
        args.insert(0, 'update')
        assert parser.parse_args(args).pre is exp

    @pytest.mark.parametrize('args, exp', (
        ([], None),
        (['--download-directory', 'foo'], 'foo'),
    ))
    def test_download_directory(self, parser, args, exp):
        """Test specifying the execute flag."""
        args.insert(0, 'update')
        assert parser.parse_args(args).download_directory is exp


class TestReadyMades(object):
    """Test generating ready-made configs."""

    def test_get_default(self):
        """Test getting the default config."""
        conf = config.ConfigFactory().get_default()
        assert any(d in conf for d in vars(config._Defaults))
        for default, value in vars(config._Defaults).items():
            if default in conf:
                if default == 'roots':
                    assert getattr(conf, default) == (
                        [expanduser(v) for v in value]
                    )
                elif default == 'authenticate':
                    assert getattr(conf, default) == (
                        [a for a in value.split()]
                    )
                else:
                    assert getattr(conf, default) == value

    def test_get_default_specify_subcommand(self):
        """Test getting default args for a non-default subcommand."""
        conf = config.ConfigFactory().get_default(subcommand='update')
        exp_defaults = (
            ('execute', False),
            ('pre', False),
            ('download_directory', None)
        )
        for default, value in exp_defaults:
            assert getattr(conf, default) is value

    def test_get_parsed(self, monkeypatch):
        """Test getting a Namespace from commandline args."""
        monkeypatch.setattr(
            argparse._sys,
            'argv',
            ['pypiserver', 'run', '--interface', '1.2.3.4']
        )
        conf = config.ConfigFactory().get_parsed()
        assert conf.host == '1.2.3.4'

    def test_from_kwargs(self):
        """Test getting a default config updated with provided kwargs."""
        conf = config.ConfigFactory().from_kwargs(
            port=9999,
            foo='foo',
        )
        assert conf.port == 9999
        assert conf.foo == 'foo'
