#! /usr/bin/env python
"""
.. NOTE:: To the developer:
    This module is moved to the root of the standalone zip-archive,
    to be used as its entry-point. Therefore DO NOT import relative.
"""
from __future__ import print_function

import getopt
import logging
import os
import re
import sys
import textwrap

import functools as ft


log = logging.getLogger('pypiserver.main')


def init_logging(level=None, frmt=None, filename=None):
    logging.basicConfig(level=level, format=frmt)
    rlog = logging.getLogger()
    rlog.setLevel(level)
    if filename:
        rlog.addHandler(logging.FileHandler(filename))


def usage():
    return textwrap.dedent("""\
  pypi-server [OPTIONS] [PACKAGES_DIRECTORY...]
    start PyPI compatible package server serving packages from
    PACKAGES_DIRECTORY. If PACKAGES_DIRECTORY is not given on the
    command line, it uses the default ~/packages.  pypiserver scans this
    directory recursively for packages. It skips packages and
    directories starting with a dot. Multiple package directories can be
    specified.

  pypi-server understands the following options:

    -p, --port PORT
      Listen on port PORT (default: 8080).

    -i, --interface INTERFACE
      Listen on interface INTERFACE (default: 0.0.0.0, any interface).

    -a, --authenticate (update|download|list), ...
      Comma-separated list of (case-insensitive) actions to authenticate.
      Requires to have set the password (-P option).
      To password-protect package downloads (in addition to uploads) while
      leaving listings public, use:
        -P foo/htpasswd.txt -a update,download
      To allow unauthorized access, use:
        -P . -a .
      Note that when uploads are not protected, the `register` command
      is not necessary, but `~/.pypirc` still need username and password fields,
      even if bogus.
      By default, only 'update' is password-protected.

    -P, --passwords PASSWORD_FILE
      Use apache htpasswd file PASSWORD_FILE to set usernames & passwords when
      authenticating certain actions (see -a option).
      To allow unauthorized access, use:
        -P . -a .

    --disable-fallback
      Disable redirect to real PyPI index for packages not found in the
      local index.

    --fallback-url FALLBACK_URL
      For packages not found in the local index, this URL will be used to
      redirect to (default: https://pypi.org/simple/).

    --server METHOD
      Use METHOD to run the server. Valid values include paste,
      cherrypy, twisted, gunicorn, gevent, wsgiref, auto. The
      default is to use "auto" which chooses one of paste, cherrypy,
      twisted or wsgiref.

    -r, --root PACKAGES_DIRECTORY
      [deprecated] Serve packages from PACKAGES_DIRECTORY.

    -o, --overwrite
      Allow overwriting existing package files.

    --hash-algo ALGO
      Any `hashlib` available algo used as fragments on package links.
      Set one of (0, no, off, false) to disabled it (default: md5).

    --welcome HTML_FILE
      Uses the ASCII contents of HTML_FILE as welcome message response.

    -v
      Enable verbose logging; repeat for more verbosity.

    --log-conf <FILE>
      read logging configuration from FILE.
      By default, configuration is read from `log.conf` if found in server's dir.

    --log-file <FILE>
      Write logging info into this FILE.

    --log-frmt <FILE>
      The logging format-string.  (see `logging.LogRecord` class from standard python library)
      [Default: %(asctime)s|%(name)s|%(levelname)s|%(thread)d|%(message)s]

    --log-req-frmt FORMAT
      A format-string selecting Http-Request properties to log; set to  '%s' to see them all.
      [Default: %(bottle.request)s]

    --log-res-frmt FORMAT
      A format-string selecting Http-Response properties to log; set to  '%s' to see them all.
      [Default: %(status)s]

    --log-err-frmt FORMAT
      A format-string selecting Http-Error properties to log; set to  '%s' to see them all.
      [Default: %(body)s: %(exception)s \n%(traceback)s]

    --cache-control AGE
      Add "Cache-Control: max-age=AGE, public" header to package downloads.
      Pip 6+ needs this for caching.


  pypi-server -h, --help
    Show this help message.

  pypi-server --version
    Show pypi-server's version.

  pypi-server -U [OPTIONS] [PACKAGES_DIRECTORY...]
    Update packages in PACKAGES_DIRECTORY. This command searches
    pypi.org for updates and shows a pip command line which
    updates the package.

  The following additional options can be specified with -U:

    -x
      Execute the pip commands instead of only showing them.

    -d DOWNLOAD_DIRECTORY
      Download package updates to this directory. The default is to use
      the directory which contains the latest version of the package to
      be updated.

    -u
      Allow updating to unstable version (alpha, beta, rc, dev versions).

  Visit https://pypi.org/project/pypiserver/ for more information.
  """)


def main(argv=None):
    import pypiserver

    if argv is None:
        argv = sys.argv

    command = "serve"

    c = pypiserver.Configuration(**pypiserver.default_config())

    update_dry_run = True
    update_directory = None
    update_stable_only = True

    try:
        opts, roots = getopt.getopt(argv[1:], "i:p:a:r:d:P:Uuvxoh", [
            "interface=",
            "passwords=",
            "authenticate=",
            "port=",
            "root=",
            "server=",
            "fallback-url=",
            "disable-fallback",
            "overwrite",
            "hash-algo=",
            "log-file=",
            "log-frmt=",
            "log-req-frmt=",
            "log-res-frmt=",
            "log-err-frmt=",
            "welcome=",
            "cache-control=",
            "version",
            "help"
        ])
    except getopt.GetoptError:
        err = sys.exc_info()[1]
        sys.exit("usage error: %s" % (err,))

    for k, v in opts:
        if k in ("-p", "--port"):
            try:
                c.port = int(v)
            except Exception:
                err = sys.exc_info()[1]
                sys.exit("Invalid port(%r) due to: %s" % (v, err))
        elif k in ("-a", "--authenticate"):
            c.authenticated = [a.lower()
                               for a in re.split("[, ]+", v.strip(" ,"))
                               if a]
            if c.authenticated == ['.']:
                c.authenticated = []
            else:
                actions = ("list", "download", "update")
                for a in c.authenticated:
                    if a not in actions:
                        errmsg = "Action '%s' for option `%s` not one of %s!"
                        sys.exit(errmsg % (a, k, actions))
        elif k in ("-i", "--interface"):
            c.host = v
        elif k in ("-r", "--root"):
            roots.append(v)
        elif k == "--disable-fallback":
            c.redirect_to_fallback = False
        elif k == "--fallback-url":
            c.fallback_url = v
        elif k == "--server":
            c.server = v
        elif k == "--welcome":
            c.welcome_file = v
        elif k == "--version":
            print("pypiserver %s\n" % pypiserver.__version__)
            return
        elif k == "-U":
            command = "update"
        elif k == "-x":
            update_dry_run = False
        elif k == "-u":
            update_stable_only = False
        elif k == "-d":
            update_directory = v
        elif k in ("-P", "--passwords"):
            c.password_file = v
        elif k in ("-o", "--overwrite"):
            c.overwrite = True
        elif k == "--hash-algo":
            c.hash_algo = None if not pypiserver.str2bool(v, c.hash_algo) else v
        elif k == "--log-file":
            c.log_file = v
        elif k == "--log-frmt":
            c.log_frmt = v
        elif k == "--log-req-frmt":
            c.log_req_frmt = v
        elif k == "--log-res-frmt":
            c.log_res_frmt = v
        elif k == "--log-err-frmt":
            c.log_err_frmt = v
        elif k == "--cache-control":
            c.cache_control = v
        elif k == "-v":
            c.verbosity += 1
        elif k in ("-h", "--help"):
            print(usage())
            sys.exit(0)

    if (not c.authenticated and c.password_file != '.' or
            c.authenticated and c.password_file == '.'):
        auth_err = "When auth-ops-list is empty (-a=.), password-file (-P=%r) must also be empty ('.')!"
        sys.exit(auth_err % c.password_file)

    if len(roots) == 0:
        roots.append(os.path.expanduser("~/packages"))

    roots=[os.path.abspath(x) for x in roots]
    c.root = roots

    verbose_levels=[
        logging.WARNING, logging.INFO, logging.DEBUG, logging.NOTSET]
    log_level=list(zip(verbose_levels, range(c.verbosity)))[-1][0]
    init_logging(level=log_level, filename=c.log_file, frmt=c.log_frmt)

    if command == "update":
        from pypiserver.manage import update_all_packages
        update_all_packages(roots, update_directory,
                dry_run=update_dry_run, stable_only=update_stable_only)
        return

    # Fixes #49:
    #    The gevent server adapter needs to patch some
    #    modules BEFORE importing bottle!
    if c.server and c.server.startswith('gevent'):
        import gevent.monkey  # @UnresolvedImport
        gevent.monkey.patch_all()

    from pypiserver import bottle
    if c.server not in bottle.server_names:
        sys.exit("unknown server %r. choose one of %s" % (
            c.server, ", ".join(bottle.server_names.keys())))

    bottle.debug(c.verbosity > 1)
    bottle._stderr = ft.partial(pypiserver._logwrite,
            logging.getLogger(bottle.__name__), logging.INFO)
    app = pypiserver.app(**vars(c))
    bottle.run(app=app, host=c.host, port=c.port, server=c.server)


if __name__ == "__main__":
    main()
