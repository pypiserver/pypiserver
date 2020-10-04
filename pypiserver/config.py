"""Pypiserver configuration management."""

import argparse
import textwrap
import typing as t

from pypiserver import __version__


def get_parser() -> argparse.ArgumentParser:
    """Return an ArgumentParser."""
    parser = argparse.ArgumentParser(
        description=textwrap.dedent(
            """\
            start PyPI compatible package server serving packages from
            PACKAGES_DIRECTORY. If PACKAGES_DIRECTORY is not given on the
            command line, it uses the default ~/packages. pypiserver scans
            this directory recursively for packages. It skips packages and
            directories starting with a dot. Multiple package directories
            may be specified."""
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8080,
        help="Listen on port PORT (default: 8080)",
    )
    parser.add_argument(
        "-i",
        "--interface",
        default="0.0.0.0",
        help="Listen on interface INTERFACE (default: 0.0.0.0)",
    )
    parser.add_argument(
        "-a",
        "--authenticate",
        default="update",
        help=textwrap.dedent(
            """\
            Comma-separated list of (case-insensitive) actions to authenticate
            (options: download, list, update, default: update). Use `.` for
            no authentication, e.g. `pypi-server -a . -P .`

            See the `-P` option for configuring users and passwords.

            Note that when uploads are not protected, the `register` command
            is not necessary, but `~/.pypirc` still needs username and
            password fields, even if bogus."""
        ),
    )
    parser.add_argument(
        "-P",
        "--passwords",
        metavar="PASSWORD_FILE",
        help=textwrap.dedent(
            """\
            Use an apache htpasswd file PASSWORD_FILE to set usernames and
            passwords for authentication. To allow unauthorized access, use:
            `pypi-server -a . -P .`
            """
        ),
    )
    parser.add_argument(
        "--disable-fallback",
        action="store_true",
        help=(
            "Disable the default redirect to PyPI for packages not found in "
            "the local index."
        ),
    )
    parser.add_argument(
        "--fallback-url",
        default="https://pypi.org/simple/",
        help=(
            "Redirect to FALLBACK_URL for packages not found in the local "
            "index."
        ),
    )
    parser.add_argument(
        "--server",
        metavar="METHOD",
        default="auto",
        help=textwrap.dedent(
            """\
            Use METHOD to run th eserver. Valid values include paste, cherrypy,
            twisted, gunicorn, gevent, wsgiref, and auto. The default is to
            use "auto", which chooses one of paste, cherrypy, twisted, or
            wsgiref.
            """
        ),
    )
    parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing package files during upload.",
    )
    parser.add_argument(
        "--hash-algo",
        default="md5",
        help=textwrap.dedent(
            """\
           Any `hashlib` available algorithm to use for generating fragments on
           package links. Can be disabled with one of (0, no, off, false).
           """
        ),
    )
    parser.add_argument(
        "--welcome",
        metavar="HTML_FILE",
        help=(
            "Use the ASCII contents of HTML_FILE as a custom welcome message "
            "on the home page."
        ),
    )
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
        choices=("stdout", "stderr", "none"),
        type=str.lower,
        help=(
            "Log messages to the specified STREAM. Valid values are stdout, "
            "stderr, and none"
        ),
    )
    parser.add_argument(
        "--log-frmt",
        metavar="FORMAT",
        default="%(asctime)s|%(name)s|%(levelname)s|%(thread)d|%(message)s",
        help=(
            "The logging format-string.  (see `logging.LogRecord` class from "
            "standard python library)"
        ),
    )
    parser.add_argument(
        "--log-req-frmt",
        metavar="FORMAT",
        default="%(bottle.request)s",
        help=(
            "A format-string selecting Http-Request properties to log; set "
            "to '%s' to see them all."
        ),
    )
    parser.add_argument(
        "--log-res-frmt",
        metavar="FORMAT",
        default="%(status)s",
        help=(
            "A format-string selecting Http-Response properties to log; set "
            "to '%s' to see them all."
        ),
    )
    parser.add_argument(
        "--log-err-frmt",
        metavar="FORMAT",
        default="%(body)s: %(exception)s \n%(traceback)s",
        help=(
            "A format-string selecting Http-Error properties to log; set "
            "to '%s' to see them all."
        ),
    )
    parser.add_argument(
        "--cache-control",
        metavar="AGE",
        type=int,
        help=(
            'Add "Cache-Control: max-age=AGE" header to package downloads. '
            "Pip 6+ requires this for caching."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=__version__,
    )
    return parser


print(get_parser().parse_args(["--help"]))
