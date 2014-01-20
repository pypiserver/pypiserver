#! /usr/bin/env python
"""minimal PyPI like server for use with pip/easy_install"""

import os, sys, getopt, re, mimetypes, warnings, itertools

warnings.filterwarnings("ignore", "Python 2.5 support may be dropped in future versions of Bottle")
from pypiserver import bottle, __version__, app
sys.modules["bottle"] = bottle
from bottle import run, server_names

mimetypes.add_type("application/octet-stream", ".egg")
mimetypes.add_type("application/octet-stream", ".whl")

DEFAULT_SERVER = None

# --- the following two functions were copied from distribute's pkg_resources module
component_re = re.compile(r'(\d+ | [a-z]+ | \.| -)', re.VERBOSE)
replace = {'pre': 'c', 'preview': 'c', '-': 'final-', 'rc': 'c', 'dev': '@'}.get


def _parse_version_parts(s):
    for part in component_re.split(s):
        part = replace(part, part)
        if part in ['', '.']:
            continue
        if part[:1] in '0123456789':
            yield part.zfill(8)    # pad for numeric comparison
        else:
            yield '*' + part

    yield '*final'  # ensure that alpha/beta/candidate are before final


def parse_version(s):
    parts = []
    for part in _parse_version_parts(s.lower()):
        if part.startswith('*'):
            # remove trailing zeros from each series of numeric parts
            while parts and parts[-1] == '00000000':
                parts.pop()
        parts.append(part)
    return tuple(parts)

# -- end of distribute's code

_archive_suffix_rx = re.compile(r"(\.zip|\.tar\.gz|\.tgz|\.tar\.bz2|-py[23]\.\d-.*|\.win-amd64-py[23]\.\d\..*|\.win32-py[23]\.\d\..*)$", re.IGNORECASE)

wheel_file_re = re.compile(
    r"""^(?P<namever>(?P<name>.+?)-(?P<ver>\d.*?))
    ((-(?P<build>\d.*?))?-(?P<pyver>.+?)-(?P<abi>.+?)-(?P<plat>.+?)
    \.whl|\.dist-info)$""",
    re.VERBOSE)


def _guess_pkgname_and_version_wheel(basename):
    m = wheel_file_re.match(basename)
    if not m:
        return None, None
    name = m.group("name")
    ver = m.group("ver")
    build = m.group("build")
    if build:
        return name, ver + "-" + build
    else:
        return name, ver


def guess_pkgname_and_version(path):
    path = os.path.basename(path)
    if path.endswith(".whl"):
        return _guess_pkgname_and_version_wheel(path)

    path = _archive_suffix_rx.sub('', path)
    if '-' not in path:
        pkgname, version = path, ''
    elif path.count('-') == 1:
        pkgname, version = path.split('-', 1)
    elif '.' not in path:
        pkgname, version = path.rsplit('-', 1)
    else:
        parts = re.split(r'-(?=(?i)v?\d+[\.a-z])', path)
        pkgname = '-'.join(parts[:-1])
        version = parts[-1]
    return pkgname, version


def normalize_pkgname(name):
    return name.lower().replace("-", "_")


def is_allowed_path(path_part):
    p = path_part.replace("\\", "/")
    return not (p.startswith(".") or "/." in p)


class pkgfile(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __repr__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            ", ".join(["%s=%r" % (k, v) for k, v in sorted(self.__dict__.items())]))


def listdir(root):
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [x for x in dirnames if is_allowed_path(x)]
        for x in filenames:
            fn = os.path.join(root, dirpath, x)
            if not is_allowed_path(x) or not os.path.isfile(fn):
                continue
            pkgname, version = guess_pkgname_and_version(x)
            if pkgname:
                yield pkgfile(fn=fn, root=root, relfn=fn[len(root) + 1:],
                              pkgname=pkgname,
                              version=version,
                              parsed_version=parse_version(version))


def find_packages(pkgs, prefix=""):
    prefix = normalize_pkgname(prefix)
    for x in pkgs:
        if prefix and normalize_pkgname(x.pkgname) != prefix:
            continue
        yield x


def get_prefixes(pkgs):
    pkgnames = set()
    eggs = set()

    for x in pkgs:
        if x.pkgname:
            if x.relfn.endswith(".egg"):
                eggs.add(x.pkgname)
            else:
                pkgnames.add(x.pkgname)

    normalized_pkgnames = set(map(normalize_pkgname, pkgnames))

    for x in eggs:
        if normalize_pkgname(x) not in normalized_pkgnames:
            pkgnames.add(x)

    return pkgnames


def exists(root, filename):
    assert "/" not in filename
    dest_fn = os.path.join(root, filename)
    return os.path.exists(dest_fn)


def store(root, filename, data):
    assert "/" not in filename
    dest_fn = os.path.join(root, filename)
    dest_fh = open(dest_fn, "wb")
    dest_fh.write(data)
    dest_fh.close()
    return True


def usage():
    sys.stdout.write("""pypi-server [OPTIONS] [PACKAGES_DIRECTORY...]
  start PyPI compatible package server serving packages from
  PACKAGES_DIRECTORY. If PACKAGES_DIRECTORY is not given on the
  command line, it uses the default ~/packages.  pypiserver scans this
  directory recursively for packages. It skips packages and
  directories starting with a dot. Multiple package directories can be
  specified.

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

  -o, --overwrite
    allow overwriting existing package files

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

  --index-url INDEX_URL
    use a different pip index url while updating. The default is to use
    https://pypi.python.org/simple.

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
    index_url = "http://pypi.python.org/simple"
    password_file = None
    overwrite = False

    update_dry_run = True
    update_directory = None
    update_stable_only = True

    try:
        opts, roots = getopt.getopt(argv[1:], "i:p:r:d:P:Uuxoh", [
            "interface=",
            "index-url=",
            "passwords=",
            "port=",
            "root=",
            "server=",
            "fallback-url=",
            "disable-fallback",
            "overwrite",
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
        elif k == "--index-url":
            index_url = v
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
        elif k in ("-o", "--overwrite"):
            overwrite = True
        elif k in ("-h", "--help"):
            usage()
            sys.exit(0)

    if len(roots) == 0:
        roots.append(os.path.expanduser("~/packages"))

    roots = [os.path.abspath(x) for x in roots]


    if command == "update":
        packages = frozenset(itertools.chain(*[listdir(r) for r in roots]))
        from pypiserver import manage
        manage.update(packages, update_directory, update_dry_run, stable_only=update_stable_only, index_url=index_url)
        return

    a = app(
        root=roots,
        redirect_to_fallback=redirect_to_fallback,
        password_file=password_file,
        fallback_url=fallback_url,
        overwrite=overwrite,
    )
    server = server or "auto"
    sys.stdout.write("This is pypiserver %s serving %r on http://%s:%s\n\n" % (__version__, ", ".join(roots), host, port))
    sys.stdout.flush()
    run(app=a, host=host, port=port, server=server)


if __name__ == "__main__":
    main(sys.argv)
