"""Management operations for pypiserver."""

from __future__ import absolute_import, print_function, unicode_literals

import itertools
import os
import sys
from distutils.version import LooseVersion
from pathlib import Path
from subprocess import call
from xmlrpc.client import Server

import pip

from .backend import listdir
from .core import PkgFile
from .pkg_helpers import normalize_pkgname, parse_version


def make_pypi_client(url):
    return Server(url)


def is_stable_version(pversion):
    for x in ("*c", "*@", "*b"):
        if x in pversion:
            return False
    for x in pversion:
        if x.startswith("*final"):
            return True
        if x.startswith("*"):
            return False
    return False


def filter_stable_releases(releases):
    for pkg in releases:
        if is_stable_version(pkg.parsed_version):
            yield pkg


def filter_latest_pkgs(pkgs):
    pkgname2latest = {}

    for x in pkgs:
        pkgname = normalize_pkgname(x.pkgname)

        if pkgname not in pkgname2latest:
            pkgname2latest[pkgname] = x
        elif x.parsed_version > pkgname2latest[pkgname].parsed_version:
            pkgname2latest[pkgname] = x

    return pkgname2latest.values()


def build_releases(pkg, versions):
    for x in versions:
        parsed_version = parse_version(x)
        if parsed_version > pkg.parsed_version:
            yield PkgFile(pkgname=pkg.pkgname, version=x, replaces=pkg)


def find_updates(pkgset, stable_only=True):
    no_releases = set()
    filter_releases = filter_stable_releases if stable_only else (lambda x: x)

    def write(s):
        sys.stdout.write(s)
        sys.stdout.flush()

    latest_pkgs = frozenset(filter_latest_pkgs(pkgset))

    sys.stdout.write(
        f"checking {len(latest_pkgs)} packages for newer version\n"
    )
    need_update = set()

    pypi = make_pypi_client("https://pypi.org/pypi/")

    for count, pkg in enumerate(latest_pkgs):
        if count % 40 == 0:
            write("\n")

        pypi_versions = pypi.package_releases(pkg.pkgname)
        if pypi_versions:
            releases = filter_releases(build_releases(pkg, pypi_versions))
            status = "."
            try:
                need_update.add(max(releases, key=lambda x: x.parsed_version))
                status = "u"
            except ValueError:
                pass
        else:
            status = "e"
            no_releases.add(pkg.pkgname)

        write(status)

    write("\n\n")

    if no_releases:
        sys.stdout.write(
            f"no releases found on pypi for"
            f" {', '.join(sorted(no_releases))}\n\n"
        )

    return need_update


class PipCmd:
    """Methods for generating pip commands."""

    @staticmethod
    def update_root(pip_version):
        """Yield an appropriate root command depending on pip version."""
        # legacy_pip = StrictVersion(pip_version) < StrictVersion('10.0')
        legacy_pip = LooseVersion(pip_version) < LooseVersion("10.0")
        for part in ("pip", "-q"):
            yield part
        yield "install" if legacy_pip else "download"

    @staticmethod
    def update(
        cmd_root,
        destdir,
        pkg_name,
        pkg_version,
        index="https://pypi.org/simple",
    ):
        """Yield an update command for pip."""
        for part in cmd_root:
            yield part
        for part in ("--no-deps", "-i", index, "-d", destdir):
            yield part
        yield "{}=={}".format(pkg_name, pkg_version)


def update_package(pkg, destdir, dry_run=False):
    """Print and optionally execute a package update."""
    print(
        f"# update {pkg.pkgname} from {pkg.replaces.version} to {pkg.version}"
    )

    cmd = tuple(
        PipCmd.update(
            PipCmd.update_root(pip.__version__),
            destdir or os.path.dirname(pkg.replaces.fn),
            pkg.pkgname,
            pkg.version,
        )
    )

    print(" ".join(cmd), end="\n\n")
    if not dry_run:
        call(cmd)


def update(pkgset, destdir=None, dry_run=False, stable_only=True):
    """Print and optionally execute pip update commands.

    :param pkgset: the set of currently available packages
    :param str destdir: the destination directory for downloads
    :param dry_run: whether commands should be executed (rather than
        just being printed)
    :param stable_only: whether only stable (non prerelease) updates
        should be considered.
    """
    need_update = find_updates(pkgset, stable_only=stable_only)
    for pkg in sorted(need_update, key=lambda x: x.pkgname):
        update_package(pkg, destdir, dry_run=dry_run)


def update_all_packages(
    roots, destdir=None, dry_run=False, stable_only=True, ignorelist=None
):
    all_packages = itertools.chain.from_iterable(
        listdir(Path(r)) for r in roots
    )

    skip_packages = set(ignorelist or ())

    packages = frozenset(
        [pkg for pkg in all_packages if pkg.pkgname not in skip_packages]
    )

    update(packages, destdir, dry_run, stable_only)
