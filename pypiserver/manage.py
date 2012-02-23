
import sys, os, re
from pypiserver import core

if sys.version_info >= (3, 0):
    from xmlrpc.client import Server
else:
    from xmlrpclib import Server

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


class pkgfile(object):
    def __init__(self, path):
        self.path = path
        self.pkgname, self.version = core.guess_pkgname_and_version(path)
        self.version_info = parse_version(self.version)


def is_stable_version(pversion):
    for x in pversion:
        if x.startswith("*final"):
            return True
        if x.startswith("*"):
            return False
    return False


def filter_stable_releases(releases):
    res = []
    for pversion, version in releases:
        if is_stable_version(pversion):
            res.append((pversion, version))
    return res


def find_updates(pkgset, stable_only=True):
    no_releases = set()

    def write(s):
        sys.stdout.write(s)
        sys.stdout.flush()

    pypi = Server("http://pypi.python.org/pypi/")
    pkgname2latest = {}

    pkgfiles = [pkgfile(x) for x in pkgset.find_packages()]

    for x in pkgfiles:
        if x.pkgname not in pkgname2latest:
            pkgname2latest[x.pkgname] = x
        elif x.version_info > pkgname2latest[x.pkgname].version_info:
            pkgname2latest[x.pkgname] = x

    need_update = []

    sys.stdout.write("checking %s packages for newer version\n" % len(pkgname2latest),)
    for count, (pkgname, file) in enumerate(pkgname2latest.items()):
        if count % 40 == 0:
            write("\n")

        releases = pypi.package_releases(pkgname)

        releases = [(parse_version(x), x) for x in releases]
        if stable_only:
            releases = filter_stable_releases(releases)

        status = "."
        if releases:
            m = max(releases)
            if m[0] > file.version_info:
                file.latest_version = m[1]
                status = "u"
                # print "%s needs update from %s to %s" % (pkgname, file.version, m[1])
                need_update.append(file)
        else:
            no_releases.add(pkgname)
            status = "e"

        write(status)

    write("\n\n")

    no_releases = list(no_releases)
    if no_releases:
        no_releases.sort()
        sys.stdout.write("no releases found on pypi for %s\n\n" % (", ".join(no_releases),))
    return need_update


def update(pkgset, destdir=None, dry_run=False, stable_only=True):
    need_update = find_updates(pkgset, stable_only=stable_only)
    for x in need_update:
        sys.stdout.write("# update %s from %s to %s\n" % (x.pkgname, x.version, x.latest_version))

        cmd = ["pip", "-q", "install", "--no-deps", "-i", "http://pypi.python.org/simple",
               "-d", destdir or os.path.dirname(os.path.join(pkgset.root, x.path)),
               "%s==%s" % (x.pkgname, x.latest_version)]

        sys.stdout.write("%s\n\n" % (" ".join(cmd),))
        if not dry_run:
            os.spawnlp(os.P_WAIT, cmd[0], *cmd)


def main():
    root = sys.argv[1]
    if len(sys.argv) > 2:
        destdir = sys.argv[2]
    else:
        destdir = None

    update(core.pkgset(root), destdir, True)


if __name__ == "__main__":
    main()
