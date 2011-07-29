#! /usr/bin/env python

import os


def main():
    files = [x.strip() for x in os.popen("git ls-files")]

    def remove(n):
        try:
            files.remove(n)
        except ValueError:
            pass

    remove("make_manifest.py")

    files.sort()

    f = open("MANIFEST.in", "w")
    for x in files:
        f.write("include %s\n" % x)
    f.close()

if __name__ == '__main__':
    main()
