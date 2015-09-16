#! /usr/bin/env python

import os
import sys
import getopt
import re
import logging
from pypiserver import __version__
from textwrap import dedent

DEFAULT_SERVER = "auto"

log = logging.getLogger('pypiserver.main')


def init_logging(level=None, frmt=None, filename=None):
    logging.basicConfig(level=level, format=format)
    rlog = logging.getLogger()
    rlog.setLevel(level)
    if filename:
        rlog.addHandler(logging.FileHandler(filename))


def usage():
    return dedent("""\
  pypi-server [OPTIONS] [PACKAGES_DIRECTORY...]
    start PyPI compatible package server serving packages from
    PACKAGES_DIRECTORY. If PACKAGES_DIRECTORY is not given on the
    command line, it uses the default ~/packages.  pypiserver scans this
    directory recursively for packages. It skips packages and
    directories starting with a dot. Multiple package directories can be
    specified.

  pypi-server understands the following options:

    -p, --port PORT
      listen on port PORT (default: 8080)

    -i, --interface INTERFACE
      listen on interface INTERFACE (default: 0.0.0.0, any interface)

    -a, --authenticate (UPDATE|download|list), ...
      comma-separated list of (case-insensitive) actions to authenticate
      Requires -P option and cannot not be empty unless -P is '.'
      For example to password-protect package downloads (in addition to uploads)
      while leaving listings public, give:
        -P foo/htpasswd.txt  -a update,download
      To drop all authentications, use:
        -P .  -a ''
      By default, only 'update' is password-protected.

    -P, --passwords PASSWORD_FILE
      use apache htpasswd file PASSWORD_FILE to set usernames & passwords
      used for authentication of certain actions (see -a option).
      Set it explicitly to '.' to allow empty list of actions to authenticate;
      then no `register` command is neccessary
      (but `~/.pypirc` still need username and password fields, even if bogus).

    --disable-fallback
      disable redirect to real PyPI index for packages not found in the
      local index

    --fallback-url FALLBACK_URL
      for packages not found in the local index, this URL will be used to
      redirect to (default: http://pypi.python.org/simple)

    --server METHOD
      use METHOD to run the server. Valid values include paste,
      cherrypy, twisted, gunicorn, gevent, wsgiref, auto. The
      default is to use "auto" which chooses one of paste, cherrypy,
      twisted or wsgiref.

    -r, --root PACKAGES_DIRECTORY
      [deprecated] serve packages from PACKAGES_DIRECTORY

    -o, --overwrite
      allow overwriting existing package files

    --welcome HTML_FILE
      uses the ASCII contents of HTML_FILE as welcome message response.

    -v
      enable verbose logging;  repeat for more verbosity.

    --log-file <FILE>
      write logging info into this FILE.

    --log-frmt <FILE>
      the logging format-string.  (see `logging.LogRecord` class from standard python library)
      [Default: %(asctime)s|%(levelname)s|%(thread)d|%(message)s]

    --log-req-frmt FORMAT
      a format-string selecting Http-Request properties to log; set to  '%s' to see them all.
      [Default: %(bottle.request)s]

    --log-res-frmt FORMAT
      a format-string selecting Http-Response properties to log; set to  '%s' to see them all.
      [Default: %(status)s]

    --log-err-frmt FORMAT
      a format-string selecting Http-Error properties to log; set to  '%s' to see them all.
      [Default: %(body)s: %(exception)s \n%(traceback)s]

    --cache-control AGE
      Add "Cache-Control: max-age=AGE, public" header to package downloads.
      Pip 6+ needs this for caching.


  pypi-server -h
  pypi-server --help
    show this help message

  pypi-server --version
    show pypi-server's version

  pypi-server -U [OPTIONS] [PACKAGES_DIRECTORY...]
    update packages in PACKAGES_DIRECTORY. This command searches
    pypi.python.org for updates and shows a pip command line which
    updates the package.

  The following additional options can be specified with -U:

    -x
      execute the pip commands instead of only showing them

    -d DOWNLOAD_DIRECTORY
      download package updates to this directory. The default is to use
      the directory which contains the latest version of the package to
      be updated.

    -u
      allow updating to unstable version (alpha, beta, rc, dev versions)

  Visit https://pypi.python.org/pypi/pypiserver for more information.
  """)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    global packages

    command = "serve"
    host = "0.0.0.0"
    port = 8080
    server = DEFAULT_SERVER
    redirect_to_fallback = True
    fallback_url = "http://pypi.python.org/simple"
    authenticated = ['update']
    password_file = None
    overwrite = False
    verbosity = 1
    log_file = None
    log_frmt = "g%(asctime)s|%(levelname)s|%(thread)d|%(message)s"
    log_req_frmt = "%(bottle.request)s"
    log_res_frmt = "%(status)s"
    log_err_frmt = "%(body)s: %(exception)s \n%(traceback)s"
    welcome_file = None
    cache_control = None

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
            port = int(v)
        elif k in ("-a", "--authenticate"):
            authenticated = [a.lower()
                             for a in re.split("[, ]+", v.strip(" ,"))
                             if a]
            actions = ("list", "download", "update")
            for a in authenticated:
                if a not in actions:
                    errmsg = "Action '%s' for option `%s` not one of %s!" % (
                        a, k, actions)
                    sys.exit(errmsg)
        elif k in ("-i", "--interface"):
            host = v
        elif k in ("-r", "--root"):
            roots.append(v)
        elif k == "--disable-fallback":
            redirect_to_fallback = False
        elif k == "--fallback-url":
            fallback_url = v
        elif k == "--server":
            server = v
        elif k == "--welcome":
            welcome_file = v
        elif k == "--version":
            sys.stdout.write("pypiserver %s\n" % __version__)
            sys.exit(0)
        elif k == "-U":
            command = "update"
        elif k == "-x":
            update_dry_run = False
        elif k == "-u":
            update_stable_only = False
        elif k == "-d":
            update_directory = v
        elif k in ("-P", "--passwords"):
            password_file = v
        elif k in ("-o", "--overwrite"):
            overwrite = True
        elif k == "--log-file":
            log_file = v
        elif k == "--log-frmt":
            log_frmt = v
        elif k == "--log-req-frmt":
            log_req_frmt = v
        elif k == "--log-res-frmt":
            log_res_frmt = v
        elif k == "--log-err-frmt":
            log_err_frmt = v
        elif k == "--cache-control":
            cache_control = v
        elif k == "-v":
            verbosity += 1
        elif k in ("-h", "--help"):
            print(usage())
            sys.exit(0)

    if password_file and password_file != '.' and not authenticated:
        sys.exit(
            "Actions to authenticate (-a) must not be empty, unless password file (-P) is '.'!")

    if len(roots) == 0:
        roots.append(os.path.expanduser("~/packages"))

    roots = [os.path.abspath(x) for x in roots]

    verbose_levels = [
        logging.WARNING, logging.INFO, logging.DEBUG, logging.NOTSET]
    log_level = list(zip(verbose_levels, range(verbosity)))[-1][0]
    init_logging(level=log_level, filename=log_file, frmt=log_frmt)

    if command == "update":
        from pypiserver.manage import update_all_packages
        update_all_packages(
            roots, update_directory, update_dry_run, stable_only=update_stable_only)
        return

    # Fixes #49:
    #    The gevent server adapter needs to patch some
    #    modules BEFORE importing bottle!
    if server and server.startswith('gevent'):
        import gevent.monkey  # @UnresolvedImport
        gevent.monkey.patch_all()

    from pypiserver.bottle import server_names, run
    if server not in server_names:
        sys.exit("unknown server %r. choose one of %s" % (
            server, ", ".join(server_names.keys())))

    from pypiserver import app
    a = app(
        root=roots,
        redirect_to_fallback=redirect_to_fallback,
        authenticated=authenticated,
        password_file=password_file,
        fallback_url=fallback_url,
        overwrite=overwrite,
        log_req_frmt=log_req_frmt, log_res_frmt=log_res_frmt, log_err_frmt=log_err_frmt,
        welcome_file=welcome_file,
        cache_control=cache_control,
    )
    log.info("This is pypiserver %s serving %r on http://%s:%s\n\n",
             __version__, ", ".join(roots), host, port)
    run(app=a, host=host, port=port, server=server)


if __name__ == "__main__":
    main()
