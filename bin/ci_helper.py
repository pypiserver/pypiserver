#!/usr/bin/env python3

"""Output expected docker tags to build in CI."""

import json
import typing as t
import re
from argparse import ArgumentParser, Namespace


RELEASE_RE = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(\.post[0-9]+)?")
PRE_RELEASE_RE = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+(a|b|c|\.?dev)[0-9]+")


def parse_args() -> Namespace:
    """Parse cmdline args."""
    parser = ArgumentParser()
    parser.add_argument(
        "ref",
        help=(
            "The github ref for which CI is running. This may be a full ref "
            "like refs/tags/v1.2.3 or refs/heads/master, or just a tag/branch "
            "name like v1.2.3 or master."
        ),
    )
    parser.add_argument(
        "action",
        help=("The action to perform"),
        choices=("docker_tags", "pypi_release", "has_tags"),
    )
    return parser.parse_args()


def strip_ref_to_name(ref: str) -> str:
    """Strip a full ref to a name."""
    strips = ("refs/heads/", "refs/tags/")
    for strip in strips:
        if ref.startswith(strip):
            return ref[len(strip) :]
    return ref


def name_to_array(name: str) -> t.Tuple[str, ...]:
    """Convert a ref name to an array of tags to build."""
    tags: t.Dict[str, t.Callable[[str], bool]] = {
        # unstable for any master build
        "unstable": lambda i: i == "master",
        # latest goes for full releases
        "latest": lambda i: RELEASE_RE.fullmatch(i) is not None,
        # the tag itself for any release or pre-release tag
        name: lambda i: (
            RELEASE_RE.fullmatch(i) is not None
            or PRE_RELEASE_RE.fullmatch(i) is not None
        ),
    }
    return tuple(tag for tag, test in tags.items() if test(name))


def ref_to_json(ref: str) -> str:
    """Convert a ref to a JSON array and return it as a string."""
    array = name_to_array(strip_ref_to_name(ref))
    return json.dumps(array)


def should_deploy_to_pypi(ref: str) -> str:
    """Return a JSON bool indicating whether we should deploy to PyPI."""
    name = strip_ref_to_name(ref)
    return json.dumps(
        RELEASE_RE.fullmatch(name) is not None
        or PRE_RELEASE_RE.fullmatch(name) is not None
    )


def main() -> None:
    """Parse args and print the JSON array."""
    args = parse_args()
    action_switch: t.Dict[str, t.Callable[[], None]] = {
        "docker_tags": lambda: print(ref_to_json(args.ref)),
        "has_tags": lambda: print(
            json.dumps(len(name_to_array(strip_ref_to_name(args.ref))) > 0)
        ),
        "pypi_release": lambda: print(should_deploy_to_pypi(args.ref)),
    }
    action_switch[args.action]()


if __name__ == "__main__":
    main()
