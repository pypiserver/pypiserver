"""Pypiserver configuration management.

NOTE: THIS CONFIG IS NOT YET IN USE. It is the intended replacement for
the current config logic, but has not yet been integrated.

To add a config option:

- If it should be available for all subcommands (run, update), add it to
  the `add_common_args()` function
- If it should only be available for the `run` command, add it to the
  `run_parser` in the `get_parser()` function.
- If it should only be available for the `update` command, add it to the
  `update_parser` in the `get_parser() function`.
- Add it to the appropriate Config class, `_ConfigCommon` for global options,
  `RunConfig` for `run` options, and `UpdateConfig` for `update` options.
  - This requires adding it as an `__init__()` kwarg, setting it as an instance
    attribute in `__init__()`, and ensuring it will be parsed from the argparse
    namespace in the `kwargs_from_namespace()` method
- Ensure your config option is tested in `tests/test_config.py`.

The `Config` class is a factory class only. Config objects do not inherit from
it, but from `_ConfigCommon`. The `Config` provides the following constructors:

- `default_with_overrides(**overrides: Any)`: construct a `RunConfig` (since
  run is the default pypiserver action) with default values, applying any
  specified overrides
- `from_args(args: Optional[Sequence[str]])`: construct a config from the
  provided arguments. Depending on arguments, the config will be either a
  `RunConfig` or an `UpdateConfig`

Legacy commandline arguments did not require a subcommand. This form is
still supported, but deprecated. A warning is printing to stderr if
the legacy commandline format is used.
"""

import argparse
import contextlib
import hashlib
import io
import itertools
import logging
import pathlib
import pkg_resources
import re
import sys
import textwrap
import typing as t
from distutils.util import strtobool as strtoint

# The `passlib` requirement is optional, so we need to verify its import here.

try:
    from passlib.apache import HtpasswdFile
except ImportError:
    HtpasswdFile = None

from pypiserver import core


# The "strtobool" function in distutils does a nice job at parsing strings,
# but returns an integer. This just wraps it in a boolean call so that we
# get a bool.
strtobool: t.Callable[[str], bool] = lambda val: bool(strtoint(val))


# Specify defaults here so that we can use them in tests &c. and not need
# to update things in multiple places if a default changes.
class DEFAULTS:
    """Config defaults."""

    AUTHENTICATE = ["update"]
    FALLBACK_URL = "https://pypi.org/simple/"
    HASH_ALGO = "md5"
    INTERFACE = "0.0.0.0"
    LOG_FRMT = "%(asctime)s|%(name)s|%(levelname)s|%(thread)d|%(message)s"
    LOG_ERR_FRMT = "%(body)s: %(exception)s \n%(traceback)s"
    LOG_REQ_FRMT = "%(bottle.request)s"
    LOG_RES_FRMT = "%(status)s"
    LOG_STREAM = sys.stdout
    PACKAGE_DIRECTORIES = [pathlib.Path("~/packages").expanduser().resolve()]
    PORT = 8080
    SERVER_METHOD = "auto"


def auth_arg(arg: str) -> t.List[str]:
    """Parse the authentication argument."""
    # Split on commas, remove duplicates, remove whitespace, ensure lowercase.
    # Sort so that they'll have a consistent ordering.
    items = sorted(list(set(i.strip().lower() for i in arg.split(","))))
    # Throw for any invalid options
    if any(i not in ("download", "list", "update", ".") for i in items):
        raise ValueError(
            "Invalid authentication option. Valid values are download, list, "
            "and update, or . (for no authentication)."
        )
    # The "no authentication" option must be specified in isolation.
    if "." in items and len(items) > 1:
        raise argparse.ArgumentTypeError(
            "Invalid authentication options. `.` (no authentication) "
            "must be specified alone."
        )

    # The "." is just an indicator for no auth, so we return an empty auth list
    # if it was present.
    return [i for i in items if not i == "."]


def hash_algo_arg(arg: str) -> t.Optional[str]:
    """Parse a hash algorithm from the string."""
    if arg in hashlib.algorithms_available:
        return arg
    try:
        if not strtobool(arg):
            return None
    except ValueError:
        # strtobool raises if the string doesn't seem like a truthiness-
        # indicating string. We do want to raise in this case, but we want
        # to raise our own custom message rather than raising the ValueError
        # raised by strtobool.
        pass
    # At this point we either had an invalid hash algorithm or a truthy string
    # like 'yes' or 'true'. In either case, we want to throw an error.
    raise argparse.ArgumentTypeError(
        f"Hash algorithm '{arg}' is not available. Please select one "
        f"of {hashlib.algorithms_available}, or turn off hashing by "
        "setting --hash-algo to 'off', '0', or 'false'"
    )


def html_file_arg(arg: t.Optional[str]) -> str:
    """Parse the provided HTML file and return its contents."""
    if arg is None or arg == "pypiserver/welcome.html":
        return pkg_resources.resource_string(__name__, "welcome.html").decode(
            "utf-8"
        )
    with open(arg, "r", encoding="utf-8") as f:
        msg = f.read()
    return msg


def ignorelist_file_arg(arg: t.Optional[str]) -> t.List[str]:
    """Parse the ignorelist and return the list of ignored files."""
    if arg is None or arg == "pypiserver/no-ignores":
        return []

    fpath = pathlib.Path(arg)
    if not fpath.exists():
        raise argparse.ArgumentTypeError(f"No such ignorelist-file '{arg}'")

    try:
        lines = (ln.strip() for ln in fpath.read_text().splitlines())
        return [ln for ln in lines if ln and not ln.startswith("#")]
    except Exception as exc:
        raise argparse.ArgumentTypeError(
            f"Could not parse ignorelist-file '{arg}': {exc}"
        ) from exc


def package_directory_arg(arg: str) -> pathlib.Path:
    """Convert any package directory argument into its absolute path."""
    pkg_dir = pathlib.Path(arg).expanduser().resolve()
    try:
        # Attempt to grab the first item from the directory. The directory may
        # be empty, in which case we'll get back None, but if the directory does
        # not exist or we do not have permission to read it, we can catch th
        # OSError and exit with a useful message.
        next(pkg_dir.iterdir(), None)
    except OSError as exc:
        raise argparse.ArgumentTypeError(
            "Error: while trying to access package directory "
            f"({pkg_dir}): {exc}"
        )
    return pkg_dir


# We need to capture this at compile time, because we replace sys.stderr
# during config parsing in order to better control error output when we
# encounter legacy cmdline arguments.
_ORIG_STDERR = sys.stderr


def log_stream_arg(arg: str) -> t.Optional[t.IO]:
    """Parse the log-stream argument."""
    lower = arg.lower()
    # Convert a `none` string to a real none.
    val = lower if lower != "none" else None
    # Ensure the remaining value is a valid stream type, and return it.
    if val is None:
        return val
    if val == "stdout":
        return sys.stdout
    if val == "stderr":
        return _ORIG_STDERR
    raise argparse.ArgumentTypeError(
        "Invalid option for --log-stream. Value must be one of stdout, "
        "stderr, or none."
    )


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to a parser."""
    # Don't update at top-level to avoid circular imports in __init__
    from pypiserver import __version__

    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Enable verbose logging; repeat for more verbosity.",
    )
    parser.add_argument(
        "--log-file",
        metavar="FILE",
        help=(
            "Write logging info into this FILE, as well as to stdout or "
            "stderr, if configured."
        ),
    )
    parser.add_argument(
        "--log-stream",
        metavar="STREAM",
        default=DEFAULTS.LOG_STREAM,
        type=log_stream_arg,
        help=(
            "Log messages to the specified STREAM. Valid values are stdout, "
            "stderr, and none"
        ),
    )
    parser.add_argument(
        "--log-frmt",
        metavar="FORMAT",
        default=DEFAULTS.LOG_FRMT,
        help=(
            "The logging format-string.  (see `logging.LogRecord` class from "
            "standard python library)"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
    )


def get_parser() -> argparse.ArgumentParser:
    """Return an ArgumentParser."""
    parser = argparse.ArgumentParser(
        description=(
            "start PyPI compatible package server serving packages from "
            "PACKAGES_DIRECTORY. If PACKAGES_DIRECTORY is not given on the "
            "command line, it uses the default ~/packages. pypiserver scans "
            "this directory recursively for packages. It skips packages and "
            "directories starting with a dot. Multiple package directories "
            "may be specified."
        ),
        # formatter_class=argparse.RawTextHelpFormatter,
        formatter_class=PreserveWhitespaceRawTextHelpFormatter,
        epilog=(
            "Visit https://github.com/pypiserver/pypiserver "
            "for more information\n \n"
        ),
    )

    add_common_args(parser)

    subparsers = parser.add_subparsers(dest="cmd")

    run_parser = subparsers.add_parser(
        "run",
        formatter_class=PreserveWhitespaceRawTextHelpFormatter,
        help="Run pypiserver, serving packages from PACKAGES_DIRECTORY",
    )

    add_common_args(run_parser)

    run_parser.add_argument(
        "package_directory",
        default=DEFAULTS.PACKAGE_DIRECTORIES,
        nargs="*",
        type=package_directory_arg,
        help="The directory from which to serve packages.",
    )

    run_parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=DEFAULTS.PORT,
        help="Listen on port PORT (default: 8080)",
    )
    run_parser.add_argument(
        "-i",
        "-H",
        "--interface",
        "--host",
        dest="host",
        default=DEFAULTS.INTERFACE,
        help="Listen on interface INTERFACE (default: 0.0.0.0)",
    )
    run_parser.add_argument(
        "-a",
        "--authenticate",
        default=DEFAULTS.AUTHENTICATE,
        type=auth_arg,
        help=(
            "Comma-separated list of (case-insensitive) actions to "
            "authenticate (options: download, list, update; default: update)."
            "\n\n "
            "Any actions not specified are not authenticated, so to "
            "authenticate downloads and updates, but allow unauthenticated "
            "viewing of the package list, you would use: "
            "\n\n"
            "  pypi-server -a 'download, update' -P ./my_passwords.htaccess"
            "\n\n"
            "To disable authentication, use:"
            "\n\n"
            "  pypi-server -a . -P ."
            "\n\n"
            "See the `-P` option for configuring users and passwords. "
            "\n\n"
            "Note that when uploads are not protected, the `register` command "
            "is not necessary, but `~/.pypirc` still needs username and "
            "password fields, even if bogus."
        ),
    )
    run_parser.add_argument(
        "-P",
        "--passwords",
        metavar="PASSWORD_FILE",
        help=(
            "Use an apache htpasswd file PASSWORD_FILE to set usernames and "
            "passwords for authentication."
            "\n\n"
            "To allow unauthorized access, use:"
            "\n\n"
            "  pypi-server -a . -P ."
            "\n\n"
        ),
    )
    run_parser.add_argument(
        "--disable-fallback",
        action="store_true",
        help=(
            "Disable the default redirect to PyPI for packages not found in "
            "the local index."
        ),
    )
    run_parser.add_argument(
        "--fallback-url",
        default=DEFAULTS.FALLBACK_URL,
        help=(
            "Redirect to FALLBACK_URL for packages not found in the local "
            "index."
        ),
    )
    run_parser.add_argument(
        "--server",
        metavar="METHOD",
        default=DEFAULTS.SERVER_METHOD,
        choices=(
            "auto",
            "cherrypy",
            "gevent",
            "gunicorn",
            "paste",
            "twisted",
            "wsgiref",
        ),
        type=str.lower,
        help=(
            "Use METHOD to run the server. Valid values include paste, "
            "cherrypy, twisted, gunicorn, gevent, wsgiref, and auto. The "
            'default is to use "auto", which chooses one of paste, cherrypy, '
            "twisted, or wsgiref."
        ),
    )
    run_parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing package files during upload.",
    )
    run_parser.add_argument(
        "--hash-algo",
        default=DEFAULTS.HASH_ALGO,
        type=hash_algo_arg,
        help=(
            "Any `hashlib` available algorithm to use for generating fragments "
            "on package links. Can be disabled with one of (0, no, off, false)."
        ),
    )
    run_parser.add_argument(
        "--welcome",
        metavar="HTML_FILE",
        # we want to run our `html_file_arg` function to get our default value
        # if the value isn't provided, but if we specify `None` as a default
        # or let argparse handle the default logic, it will not call that
        # function with the None value. So, we set it to a custom value.
        default="pypiserver/welcome.html",
        type=html_file_arg,
        help=(
            "Use the contents of HTML_FILE as a custom welcome message "
            "on the home page."
        ),
    )
    run_parser.add_argument(
        "--cache-control",
        metavar="AGE",
        type=int,
        help=(
            'Add "Cache-Control: max-age=AGE" header to package downloads. '
            "Pip 6+ requires this for caching."
        ),
    )
    run_parser.add_argument(
        "--log-req-frmt",
        metavar="FORMAT",
        default=DEFAULTS.LOG_REQ_FRMT,
        help=(
            "A format-string selecting Http-Request properties to log; set "
            "to '%%s' to see them all."
        ),
    )
    run_parser.add_argument(
        "--log-res-frmt",
        metavar="FORMAT",
        default=DEFAULTS.LOG_RES_FRMT,
        help=(
            "A format-string selecting Http-Response properties to log; set "
            "to '%%s' to see them all."
        ),
    )
    run_parser.add_argument(
        "--log-err-frmt",
        metavar="FORMAT",
        default=DEFAULTS.LOG_ERR_FRMT,
        help=(
            "A format-string selecting Http-Error properties to log; set "
            "to '%%s' to see them all."
        ),
    )

    update_parser = subparsers.add_parser(
        "update",
        help=textwrap.dedent(
            "Handle updates of packages managed by pypiserver. By default, "
            "a pip command to update the packages is printed to stdout for "
            "introspection or pipelining. See the `-x` option for updating "
            "packages directly."
        ),
    )

    add_common_args(update_parser)

    update_parser.add_argument(
        "package_directory",
        default=DEFAULTS.PACKAGE_DIRECTORIES,
        nargs="*",
        type=package_directory_arg,
        help="The directory from which to serve packages.",
    )

    update_parser.add_argument(
        "-x",
        "--execute",
        action="store_true",
        help="Execute the pip commands rather than printing to stdout",
    )
    update_parser.add_argument(
        "-d",
        "--download-directory",
        help=(
            "Specify a directory where packages updates will be downloaded. "
            "The default behavior is to use the directory which contains "
            "the package being updated."
        ),
    )
    update_parser.add_argument(
        "-u",
        "--allow-unstable",
        action="store_true",
        help=(
            "Allow updating to unstable versions (alpha, beta, rc, dev, etc.)"
        ),
    )
    update_parser.add_argument(
        "--blacklist-file",
        "--ignorelist-file",
        dest="ignorelist_file",
        default="pypiserver/no-ignores",
        type=ignorelist_file_arg,
        help=(
            "Don't update packages listed in this file (one package name per "
            "line, without versions, '#' comments honored). This can be useful "
            "if you upload private packages into pypiserver, but also keep a "
            "mirror of public packages that you regularly update. Attempting "
            "to pull an update of a private package from `pypi.org` might pose "
            "a security risk - e.g. a malicious user might publish a higher "
            "version of the private package, containing arbitrary code."
        ),
    )
    return parser


TConf = t.TypeVar("TConf", bound="_ConfigCommon")


class _ConfigCommon:
    def __init__(
        self,
        roots: t.List[pathlib.Path],
        verbosity: int,
        log_frmt: str,
        log_file: t.Optional[str],
        log_stream: t.Optional[t.IO],
    ) -> None:
        """Construct a RuntimeConfig."""
        # Global arguments
        self.verbosity = verbosity
        self.log_file = log_file
        self.log_stream = log_stream
        self.log_frmt = log_frmt
        self.roots = roots

        # Derived properties are directly based on other properties and are not
        # included in equality checks.
        self._derived_properties: t.Tuple[str, ...] = (
            "iter_packages",
            "package_root",
        )
        # The first package directory is considered the root. This is used
        # for uploads.
        self.package_root = self.roots[0]

    @classmethod
    def from_namespace(
        cls: t.Type[TConf], namespace: argparse.Namespace
    ) -> TConf:
        """Construct a config from an argparse namespace."""
        return cls(**cls.kwargs_from_namespace(namespace))

    @staticmethod
    def kwargs_from_namespace(
        namespace: argparse.Namespace,
    ) -> t.Dict[str, t.Any]:
        """Convert a namespace into __init__ kwargs for this class."""
        return dict(
            verbosity=namespace.verbose,
            log_file=namespace.log_file,
            log_stream=namespace.log_stream,
            log_frmt=namespace.log_frmt,
            roots=namespace.package_directory,
        )

    @property
    def log_level(self) -> int:
        """Return an appropriate log-level for the config's verbosity."""
        levels = {
            0: logging.WARNING,
            1: logging.INFO,
            2: logging.DEBUG,
        }
        # Return a log-level from warning through not set (log all messages).
        # If we've specified 3 or more levels of verbosity, just return not set.
        return levels.get(self.verbosity, logging.NOTSET)

    def iter_packages(self) -> t.Iterator[core.PkgFile]:
        """Iterate over packages in root directories."""
        yield from (
            itertools.chain.from_iterable(
                core.listdir(str(r)) for r in self.roots
            )
        )

    def with_updates(self: TConf, **kwargs: t.Any) -> TConf:
        """Create a new config with the specified updates.

        The current config is used as a base. Any properties not specified in
        keyword arguments will remain unchanged.
        """
        return self.__class__(**{**dict(self), **kwargs})  # type: ignore

    def __repr__(self) -> str:
        """A string representation indicating the class and its properties."""
        return "{}({})".format(
            self.__class__.__name__,
            ", ".join(
                f"{k}={v}"
                for k, v in vars(self).items()
                if not k.startswith("_")
            ),
        )

    def __eq__(self, other: t.Any) -> bool:
        """Configs are equal if their public values are equal."""
        if not isinstance(other, self.__class__):
            return False
        return all(
            getattr(other, k) == v
            for k, v in self
            if not k in self._derived_properties
        )

    def __iter__(self) -> t.Iterator[t.Tuple[str, t.Any]]:
        """Iterate over config (k, v) pairs."""
        yield from (
            (k, v)
            for k, v in vars(self).items()
            if not k.startswith("_") and k not in self._derived_properties
        )


class RunConfig(_ConfigCommon):
    """A config for the Run command."""

    def __init__(
        self,
        port: int,
        host: str,
        authenticate: t.List[str],
        password_file: t.Optional[str],
        disable_fallback: bool,
        fallback_url: str,
        server_method: str,
        overwrite: bool,
        hash_algo: t.Optional[str],
        welcome_msg: str,
        cache_control: t.Optional[int],
        log_req_frmt: str,
        log_res_frmt: str,
        log_err_frmt: str,
        auther: t.Callable[[str, str], bool] = None,
        **kwargs: t.Any,
    ) -> None:
        """Construct a RuntimeConfig."""
        super().__init__(**kwargs)
        self.port = port
        self.host = host
        self.authenticate = authenticate
        self.password_file = password_file
        self.disable_fallback = disable_fallback
        self.fallback_url = fallback_url
        self.server_method = server_method
        self.overwrite = overwrite
        self.hash_algo = hash_algo
        self.welcome_msg = welcome_msg
        self.cache_control = cache_control
        self.log_req_frmt = log_req_frmt
        self.log_res_frmt = log_res_frmt
        self.log_err_frmt = log_err_frmt

        # Derived properties
        self._derived_properties = self._derived_properties + ("auther",)
        self.auther = self.get_auther(auther)

    @classmethod
    def kwargs_from_namespace(
        cls, namespace: argparse.Namespace
    ) -> t.Dict[str, t.Any]:
        """Convert a namespace into __init__ kwargs for this class."""
        return {
            **super(RunConfig, cls).kwargs_from_namespace(namespace),
            "port": namespace.port,
            "host": namespace.host,
            "authenticate": namespace.authenticate,
            "password_file": namespace.passwords,
            "disable_fallback": namespace.disable_fallback,
            "fallback_url": namespace.fallback_url,
            "server_method": namespace.server,
            "overwrite": namespace.overwrite,
            "hash_algo": namespace.hash_algo,
            "welcome_msg": namespace.welcome,
            "cache_control": namespace.cache_control,
            "log_req_frmt": namespace.log_req_frmt,
            "log_res_frmt": namespace.log_res_frmt,
            "log_err_frmt": namespace.log_err_frmt,
        }

    def get_auther(
        self, passed_auther: t.Optional[t.Callable[[str, str], bool]]
    ) -> t.Callable[[str, str], bool]:
        """Create or retrieve an authentication function."""
        # The auther may be specified directly as a kwarg in the API interface
        if passed_auther:
            return passed_auther
        # Otherwise we check to see if we need to authenticate
        if self.password_file == "." or self.authenticate == []:
            # It's illegal to specify no authentication without also specifying
            # no password file, and vice-versa.
            if self.password_file != "." or self.authenticate != []:
                sys.exit(
                    "When auth-ops-list is empty (-a=.), password-file"
                    f" (-P={self.password_file!r}) must also be empty ('.')!"
                )
            # Return an auther that always returns true.
            return lambda _uname, _pw: True
        # Now, if there was no password file specified, we can return an auther
        # that always returns False, since there is no way to authenticate.
        if self.password_file is None:
            return lambda _uname, _pw: False
        # Finally, if a password file was specified, we'll load it up with
        # Htpasswd and return a callable that checks it.
        if HtpasswdFile is None:
            sys.exit(
                "apache.passlib library is not available. You must install "
                "pypiserver with the optional 'passlib' dependency (`pip "
                "install pypiserver['passlib']`) in order to use password "
                "authentication"
            )

        loaded_pw_file = HtpasswdFile(self.password_file)

        # Construct a local closure over the loaded PW file and return as our
        # authentication function.
        def auther(uname: str, pw: str) -> bool:
            loaded_pw_file.load_if_changed()
            return loaded_pw_file.check_password(uname, pw)

        return auther


class UpdateConfig(_ConfigCommon):
    """A config for the Update command."""

    def __init__(
        self,
        execute: bool,
        download_directory: t.Optional[str],
        allow_unstable: bool,
        ignorelist: t.List[str],
        **kwargs: t.Any,
    ) -> None:
        """Construct an UpdateConfig."""
        super().__init__(**kwargs)
        self.execute = execute
        self.download_directory = download_directory
        self.allow_unstable = allow_unstable
        self.ignorelist = ignorelist

    @classmethod
    def kwargs_from_namespace(
        cls, namespace: argparse.Namespace
    ) -> t.Dict[str, t.Any]:
        """Convert a namespace into __init__ kwargs for this class."""
        return {
            **super(UpdateConfig, cls).kwargs_from_namespace(namespace),
            "execute": namespace.execute,
            "download_directory": namespace.download_directory,
            "allow_unstable": namespace.allow_unstable,
            "ignorelist": namespace.ignorelist_file,
        }


class Config:
    """Config constructor for building a config from args."""

    @classmethod
    def default_with_overrides(cls, **overrides: t.Any) -> RunConfig:
        """Construct a RunConfig with default arguments, plus overrides.

        Overrides must be valid arguments to the `__init__()` function
        of `RunConfig`.
        """
        default_config = cls.from_args(["run"])
        assert isinstance(default_config, RunConfig)
        return default_config.with_updates(**overrides)

    @classmethod
    def from_args(
        cls, args: t.Sequence[str] = None
    ) -> t.Union[RunConfig, UpdateConfig]:
        """Construct a Config from the passed args or sys.argv."""
        # If pulling args from sys.argv (commandline arguments), argv[0] will
        # be the program name, (i.e. pypi-server), so we don't need to
        # worry about it.
        args = args if args is not None else sys.argv[1:]
        parser = get_parser()

        try:
            with capture_stderr() as cap:
                parsed = parser.parse_args(args)
            # There's a special case we need to handle where no arguments
            # whatsoever were provided. Because we need to introspect
            # what subcommand is called, via the `add_subparsers(dest='cmd')`
            # call, calling with no subparser is _not_ an error. We will
            # treat it as such, so that we then trigger the legacy argument
            # handling logic.
            if parsed.cmd is None:
                sys.exit(1)
        except SystemExit as exc:
            # A SystemExit is raised in some non-error cases, like
            # printing the help or the version. Reraise in those cases.
            cap.seek(0)
            first_txt = cap.read()
            if not exc.code or exc.code == 0:
                # There usually won't have been any error text in these
                # cases, but if there was, print it.
                if first_txt:
                    print(first_txt, file=sys.stderr)
                raise
            # Otherwise, it's possible they're using the older, non-subcommand
            # form of the CLI. In this case, attempt to parse with adjusted
            # arguments. If the parse is successful, warn them about using
            # deprecated arguments and continue. If this parse _also_ fails,
            # show them the parsing error for their original arguments,
            # not for the adjusted arguments.
            try:
                with capture_stderr() as cap:
                    parsed = parser.parse_args(cls._adjust_old_args(args))
                print(
                    "WARNING: You are using deprecated arguments to pypiserver.\n\n"
                    "Please run `pypi-server --help` and update your command "
                    "to align with the current interface.\n\n"
                    "In most cases, this will be as simple as just using\n\n"
                    "  pypi-server run [args]\n\n"
                    "instead of\n\n"
                    "  pypi-server [args]\n",
                    file=sys.stderr,
                )
            except SystemExit:
                cap.seek(0)
                second_txt = cap.read()
                if not exc.code or exc.code == 0:
                    # Again, usually nothing to stderr in these cases,
                    # but if there was, print it and re-raise.
                    if second_txt:
                        print(second_txt, file=sys.stderr)
                    raise
                # Otherwise, we print the original error text instead of
                # the error text from the call with our adjusted args,
                # and then raise. Showing the original error text will
                # provide a usage error for the new argument form, which
                # should help folks to upgrade.
                if first_txt:
                    print(first_txt, file=sys.stderr)
                raise

        if parsed.cmd == "run":
            return RunConfig.from_namespace(parsed)
        if parsed.cmd == "update":
            return UpdateConfig.from_namespace(parsed)
        raise SystemExit(parser.format_usage())

    @staticmethod
    def _adjust_old_args(args: t.Sequence[str]) -> t.List[str]:
        """Adjust args for backwards compatibility.

        Should only be called once args have been verified to be unparseable.
        """
        # Backwards compatibility hack: for most of pypiserver's life, "run"
        # and "update" were not separate subcommands. The `-U` flag being
        # present on the cmdline, regardless of other arguments, would lead
        # to update behavior. In order to allow subcommands without
        # breaking backwards compatibility, we need to insert "run" or
        # "update" as a positional arg before any other arguments.

        # We will be adding our subcommand as the first argument.
        insertion_idx = 0

        # Don't actually update the passed list, in case it was the global
        # sys.argv.
        updated_args = list(args)

        # Find the update index. For "reasons", python's index search throws
        # if the value isn't found, so manually wrap in the usual "return -1
        # if not found" standard
        try:
            update_idx = updated_args.index("-U")
        except ValueError:
            update_idx = -1

        if update_idx == -1:
            # We were a "run" command.
            updated_args.insert(insertion_idx, "run")
        else:
            # Remove the -U from the args and add the "update" command at the
            # start of the arg list.
            updated_args.pop(update_idx)
            updated_args.insert(insertion_idx, "update")

        return updated_args


@contextlib.contextmanager
def capture_stderr() -> t.Iterator[t.IO]:
    """Capture stderr and yield as a buffer."""
    orig = sys.stderr
    cap = io.StringIO()
    sys.stderr = cap
    try:
        yield cap
    finally:
        sys.stderr = orig


# Note: this is adapted from this StackOverflow answer:
# https://stackoverflow.com/a/35925919 -- the normal "raw" help
# text formatters provided with the argparse library don't do
# a great job of maintaining whitespace while still keeping
# subsequent lines properly intended.
class PreserveWhitespaceRawTextHelpFormatter(
    argparse.RawDescriptionHelpFormatter
):
    """A help text formatter allowing more customization of newlines."""

    def __add_whitespace(self, idx: int, iWSpace: int, text: str) -> str:
        if idx == 0:
            return text
        return (" " * iWSpace) + text

    def _split_lines(self, text: str, width: int) -> t.List[str]:
        textRows = text.splitlines()
        for idx, line in enumerate(textRows):
            search = re.search(r"\s*[0-9\-]{0,}\.?\s*", line)
            if line.strip() == "":
                textRows[idx] = " "
            elif search:
                lWSpace = search.end()
                lines = [
                    self.__add_whitespace(i, lWSpace, x)
                    for i, x in enumerate(textwrap.wrap(line, width))
                ]
                textRows[idx] = lines  # type: ignore

        return [item for sublist in textRows for item in sublist]
