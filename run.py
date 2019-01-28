#!/usr/bin/env python
"""Perform repetitive tasks or those that require setup.

To add a command, just create a @staticmethod in `Commands`. The
docstring will be used as the help summary for the script's usage.
"""

import typing as t
from argparse import ArgumentParser, Namespace
from functools import partial
from subprocess import run


def _exhaust(iterator: t.Iterator) -> None:
    for _ in iterator:
        pass


class Commands:
    """Actions that may be taken from the commandline.

    All actions should be @staticmethods and will receive the parsed
    args as their only input. The docstring of a given action will be
    used as its commandline help.
    """

    @classmethod
    def add_to_parser(cls, sub_parser_action):
        """Add all commands as subcommands to the given parser."""
        _exhaust(
            map(
                lambda i: sub_parser_action.add_parser(
                    i[0], help=i[1].__func__.__doc__
                ),
                sorted(cls.iter(), key=lambda i: i[0]),
            )
        )

    @classmethod
    def iter(cls) -> t.Iterator[t.Tuple[str, staticmethod]]:
        """Iterate over available commands.

        Yield 2-tuples of command names to references to the commands
        themselves.
        """
        return filter(
            lambda item: (
                isinstance(item[1], staticmethod)
                and not item[0].startswith("_")
            ),
            vars(cls).items(),
        )

    @classmethod
    def get_runner(cls, args: Namespace):
        """Get a command runner for the given args."""
        return partial(cls.run, args)

    @classmethod
    def run(cls, args: Namespace, name: str):
        """Run the command specified by the given name."""
        return getattr(cls, name)(args)

    @classmethod
    def iter_names(cls) -> t.Iterator[str]:
        """Iterate over available command names."""
        return map(lambda i: i[0], cls.iter())

    @staticmethod
    def lint(_):
        """Run linting."""
        run(("tox", "-e", "lint"))

    @staticmethod
    def test(_):
        """Run all tests and linting."""
        Commands.lint(_)
        run(("tox",))

    @staticmethod
    def utest(_):
        """Run unit tests."""
        run(("tox", "-e", "test", "--", "tests/unit"))


def create_parser():
    """Create and return an argument parser."""
    parser = ArgumentParser(description="run development or build tasks")
    subparsers = parser.add_subparsers(
        dest="command", title="available commands"
    )
    Commands.add_to_parser(subparsers)
    return parser


def main():
    """Provide an entrypoint for the script."""
    args = create_parser().parse_args()
    run_cmd = Commands.get_runner(args)
    run_cmd(args.command)


if __name__ == "__main__":
    main()
