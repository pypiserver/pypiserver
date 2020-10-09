"""Pypiserver configuration management.

NOTE: THIS CONFIG IS NOT YET IN USE. It is the intended replacement for
the current config logic, but has not yet been integrated.

To add a config option:

- If it should be available for all subcommands (run, update), add it to
  the `global_args` parser.
- If it should only be available for the `run` command, add it to the
  `run_parser`.
- If it should only be available for the `update` command, add it to the
  `update_parser`.
- Add it to the appropriate Config class, `_ConfigCommon` for global options,
  `RunConfig` for `run` options, and `UpdateConfig` for `update` options.
- Ensure your config option is tested in `tests/test_config.py`.

The `Config` class provides a `.from_args()` static method, which returns
either a `RunConfig` or an `UpdateConfig`, depending on which subcommand
is specified in the args.

Legacy commandline arguments did not require a subcommand. This form is
still supported, but deprecated. A warning is printing to stderr if
the legacy commandline format is used.

Command line arguments should be parsed as early as possible, using
custom functions like the `auth_*` functions below if needed. For example,
if an option were to take JSON as an argument, that JSON should be parsed
into a dict by the argument parser.
"""

import argparse
import contextlib
import hashlib
import io
import pkg_resources
import re
import textwrap
import sys
import typing as t

from pypiserver import __version__


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
    PACKAGE_DIRECTORIES = ["~/packages"]
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
        raise ValueError(
            "Invalid authentication options. `.` (no authentication) "
            "must be specified alone."
        )
    return items


def hash_algo_arg(arg: str) -> t.Callable:
    """Parse a hash algorithm from the string."""
    if arg not in hashlib.algorithms_available:
        raise ValueError(
            f"Hash algorithm {arg} is not available. Please select one "
            f"of {hashlib.algorithms_available}"
        )
    return getattr(hashlib, arg)


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
    with open(arg) as f:
        stripped_lines = (ln.strip() for ln in f.readlines())
        return [ln for ln in stripped_lines if ln and not ln.startswith("#")]


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
    raise ValueError(
        "Invalid option for --log-stream. Value must be one of stdout, "
        "stderr, or none."
    )


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to a parser."""
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
        "--interface",
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
            "Use METHOD to run th eserver. Valid values include paste, "
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
        choices=hashlib.algorithms_available,
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


class _ConfigCommon:
    def __init__(self, namespace: argparse.Namespace) -> None:
        """Construct a RuntimeConfig."""
        # Global arguments
        self.verbosity: int = namespace.verbose
        self.log_file: t.Optional[str] = namespace.log_file
        self.log_stream: t.Optional[t.IO] = namespace.log_stream
        self.log_frmt: str = namespace.log_frmt
        self.roots: t.List[str] = namespace.package_directory

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
        return all(getattr(other, k) == v for k, v in self)  # type: ignore

    def __iter__(self) -> t.Iterable[t.Tuple[str, t.Any]]:
        """Iterate over config (k, v) pairs."""
        yield from (
            (k, v) for k, v in vars(self).items() if not k.startswith("_")
        )


class RunConfig(_ConfigCommon):
    """A config for the Run command."""

    def __init__(self, namespace: argparse.Namespace) -> None:
        """Construct a RuntimeConfig."""
        super().__init__(namespace)
        self.port: int = namespace.port
        self.interface: str = namespace.interface
        self.authenticate: t.List[str] = namespace.authenticate
        self.password_file: t.Optional[str] = namespace.passwords
        self.disable_fallback: bool = namespace.disable_fallback
        self.fallback_url: str = namespace.fallback_url
        self.server_method: str = namespace.server
        self.overwrite: bool = namespace.overwrite
        self.hash_algo: t.Callable = namespace.hash_algo
        self.welcome_msg: str = namespace.welcome
        self.cache_control: t.Optional[int] = namespace.cache_control
        self.log_req_frmt: str = namespace.log_req_frmt
        self.log_res_frmt: str = namespace.log_res_frmt
        self.log_err_frmt: str = namespace.log_err_frmt


class UpdateConfig(_ConfigCommon):
    """A config for the Update command."""

    def __init__(self, namespace: argparse.Namespace) -> None:
        """Construct an UpdateConfig."""
        super().__init__(namespace)
        self.execute: bool = namespace.execute
        self.download_directory: t.Optional[str] = namespace.download_directory
        self.allow_unstable: bool = namespace.allow_unstable
        self.ignorelist: t.List[str] = namespace.ignorelist_file


class Config:
    """Config constructor for building a config from args."""

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
            return RunConfig(parsed)
        if parsed.cmd == "update":
            return UpdateConfig(parsed)
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
        args = list(args)

        # Find the update index. For "reasons", python's index search throws
        # if the value isn't found, so manually wrap in the usual "return -1
        # if not found" standard
        try:
            update_idx = args.index("-U")
        except ValueError:
            update_idx = -1

        if update_idx == -1:
            # We were a "run" command.
            args.insert(insertion_idx, "run")
        else:
            # Remove the -U from the args and add the "update" command at the
            # start of the arg list.
            args.pop(update_idx)
            args.insert(insertion_idx, "update")

        return args


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
