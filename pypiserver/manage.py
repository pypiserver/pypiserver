
import sys, os, xmlrpclib, pkg_resources
from pypiserver import core


class pkgfile(object):
    def __init__(self, path):
        self.path = path
        self.pkgname, self.version = core.guess_pkgname_and_version(path)
        self.version_info = pkg_resources.parse_version(self.version)


def find_updates(pkgset):
    def write(s):
        sys.stdout.write(s)
        sys.stdout.flush()

    pypi = xmlrpclib.Server("http://pypi.python.org/pypi/")
    pkgname2latest = {}

    pkgfiles = [pkgfile(x) for x in pkgset.find_packages()]

    for x in pkgfiles:
        if x.pkgname not in pkgname2latest:
            pkgname2latest[x.pkgname] = x
        elif x.version_info > pkgname2latest[x.pkgname].version_info:
            pkgname2latest[x.pkgname] = x

    need_update = []

    print "checking %s packages for newer version" % len(pkgname2latest),
    for count, (pkgname, file) in enumerate(pkgname2latest.items()):
        if count % 40 == 0:
            write("\n")

        releases = pypi.package_releases(pkgname)

        releases = [(pkg_resources.parse_version(x), x) for x in releases]
        do_update = False
        if releases:
            m = max(releases)
            if m[0] > file.version_info:
                file.latest_version = m[1]
                do_update = True
                # print "%s needs update from %s to %s" % (pkgname, file.version, m[1])
                need_update.append(file)
        if do_update:
            write("U")
        else:
            write(".")

    write("\n\n")

    return need_update


def update(pkgset, destdir=None, dry_run=False):
    need_update = find_updates(pkgset)
    for x in need_update:
        print "# update", x.pkgname, "from", x.version, "to", x.latest_version

        cmd = ["pip", "-q", "install", "-i", "http://pypi.python.org/simple",
               "-d", destdir or os.path.dirname(os.path.join(pkgset.root, x.path)),
               "%s==%s" % (x.pkgname, x.latest_version)]
        print " ".join(cmd)
        print
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
