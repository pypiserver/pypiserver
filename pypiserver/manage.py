
import sys, os
from pypiserver import core

if sys.version_info >= (3, 0):
    from xmlrpc.client import Server
else:
    from xmlrpclib import Server


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

    for x in pkgset:
        if x.pkgname not in pkgname2latest:
            pkgname2latest[x.pkgname] = x
        elif x.parsed_version > pkgname2latest[x.pkgname].parsed_version:
            pkgname2latest[x.pkgname] = x

    need_update = []

    sys.stdout.write("checking %s packages for newer version\n" % len(pkgname2latest),)
    for count, (pkgname, file) in enumerate(pkgname2latest.items()):
        if count % 40 == 0:
            write("\n")

        releases = pypi.package_releases(pkgname)

        releases = [(core.parse_version(x), x) for x in releases]
        if stable_only:
            releases = filter_stable_releases(releases)

        status = "."
        if releases:
            m = max(releases)
            if m[0] > file.parsed_version:
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
               "-d", destdir or os.path.dirname(x.fn),
               "%s==%s" % (x.pkgname, x.latest_version)]

        sys.stdout.write("%s\n\n" % (" ".join(cmd),))
        if not dry_run:
            os.spawnlp(os.P_WAIT, cmd[0], *cmd)
