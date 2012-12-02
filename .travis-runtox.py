#! /usr/bin/env python


def main():
    import sys, os
    if hasattr(sys, "pypy_version_info"):
        v = "pypy"
    else:
        v = "py%s%s" % (sys.version_info[:2])

    os.execvp("tox", ["tox", "-e", v])


if __name__ == "__main__":
    main()
