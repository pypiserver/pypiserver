#! /usr/bin/env python
"""minimal PyPI like server for use with pip/easy_install"""

import os, sys, getopt, re, mimetypes, warnings

warnings.filterwarnings("ignore", "Python 2.5 support may be dropped in future versions of Bottle")
from pypiserver import bottle, __version__, app
sys.modules["bottle"] = bottle
from bottle import run, server_names

mimetypes.add_type("application/octet-stream", ".egg")

DEFAULT_SERVER = None


def guess_pkgname(path):
    pkgname = re.split(r"-\d+", os.path.basename(path))[0]
    return pkgname

_archive_suffix_rx = re.compile(r"(\.zip|\.tar\.gz|\.tgz|\.tar\.bz2|-py[23]\.\d-.*|\.win-amd64-py[23]\.\d\..*|\.win32-py[23]\.\d\..*)$", re.IGNORECASE)


def guess_pkgname_and_version(path):
    path = os.path.basename(path)
    pkgname = re.split(r"-\d+", path, 1)[0]
    version = path[len(pkgname) + 1:]
    version = _archive_suffix_rx.sub("", version)
    return pkgname, version


def is_allowed_path(path_part):
    p = path_part.replace("\\", "/")
    return not (p.startswith(".") or "/." in p)


class pkgset(object):
    def __init__(self, root):
        self.root = os.path.abspath(root)

    def listdir(self):
        res = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [x for x in dirnames if is_allowed_path(x)]
            for x in filenames:
                if is_allowed_path(x):
                    res.append(os.path.join(self.root, dirpath, x))
        return res

    def find_packages(self, prefix=""):
        prefix = prefix.lower()
        files = []
        for x in self.listdir():
            pkgname = guess_pkgname(x)
            if prefix and pkgname.lower() != prefix:
                continue
            if os.path.isfile(x):
                files.append(x[len(self.root) + 1:])
        return files

    def find_prefixes(self):
        prefixes = set()
        for x in self.listdir():
            if not os.path.isfile(x):
                continue

            pkgname = guess_pkgname(x)
            if pkgname:
                prefixes.add(pkgname)
        return prefixes

    def store(self, filename, data):
        assert "/" not in filename
        dest_fn = os.path.join(self.root, filename)
        if not os.path.exists(dest_fn):
            dest_fh = open(dest_fn, "wb")

            dest_fh.write(data)
            dest_fh.close()
            return True

        return False


def usage():
    sys.stdout.write("""pypi-server [OPTIONS] [PACKAGES_DIRECTORY]
  start PyPI compatible package server serving packages from
  PACKAGES_DIRECTORY. If PACKAGES_DIRECTORY is not given on the
  command line, it uses the default ~/packages.  pypiserver scans this
  directory recursively for packages. It skips packages and
  directories starting with a dot.

pypi-server understands the following options:

  -p PORT, --port PORT
    listen on port PORT (default: 8080)

  -i INTERFACE, --interface INTERFACE
    listen on interface INTERFACE (default: 0.0.0.0, any interface)

  -P PASSWORD_FILE, --passwords PASSWORD_FILE
    use apache htpasswd file PASSWORD_FILE in order to enable password
    protected uploads.

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

  -r PACKAGES_DIRECTORY, --root PACKAGES_DIRECTORY
    [deprecated] serve packages from PACKAGES_DIRECTORY

pypi-server -h
pypi-server --help
  show this help message

pypi-server --version
  show pypi-server's version

pypi-server -U [OPTIONS] [PACKAGES_DIRECTORY]
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

Visit http://pypi.python.org/pypi/pypiserver for more information.
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
    password_file = None

    update_dry_run = True
    update_directory = None
    update_stable_only = True

    try:
        opts, roots = getopt.getopt(argv[1:], "i:p:r:d:P:Uuxh", [
            "interface=",
            "passwords=",
            "port=",
            "root=",
            "server=",
            "fallback-url=",
            "disable-fallback",
            "version",
            "help"
        ])
    except getopt.GetoptError:
        err = sys.exc_info()[1]
        sys.exit("usage error: %s" % (err,))

    for k, v in opts:
        if k in ("-p", "--port"):
            port = int(v)
        elif k in ("-i", "--interface"):
            host = v
        elif k in ("-r", "--root"):
            roots.append(v)
        elif k == "--disable-fallback":
            redirect_to_fallback = False
        elif k == "--fallback-url":
            fallback_url = v
        elif k == "--server":
            if v not in server_names:
                sys.exit("unknown server %r. choose one of %s" % (
                    v, ", ".join(server_names.keys())))
            server = v
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
        elif k in ("-h", "--help"):
            usage()
            sys.exit(0)

    if len(roots) == 0:
        roots.append(os.path.expanduser("~/packages"))
    elif len(roots) > 1:
        sys.exit("Error: more than one root directory specified: %r" % (roots,))

    root = os.path.abspath(roots[0])

    try:
        os.listdir(root)
    except Exception:
        err = sys.exc_info()[1]
        sys.exit("Error: while trying to list %r: %s" % (root, err))


    if command == "update":
        packages = pkgset(root)
        from pypiserver import manage
        manage.update(packages, update_directory, update_dry_run, stable_only=update_stable_only)
        return

    a = app(
        root=root,
        redirect_to_fallback=redirect_to_fallback,
        password_file=password_file,
        fallback_url=fallback_url
    )
    server = server or "auto"
    sys.stdout.write("This is pypiserver %s serving %r on http://%s:%s\n\n" % (__version__, root, host, port))
    sys.stdout.flush()
    run(app=a, host=host, port=port, server=server)


if __name__ == "__main__":
    main(sys.argv)
