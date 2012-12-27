#! /usr/bin/env python

import os


def main():
    files = sorted(set([x.strip() for x in os.popen("git ls-files")]) -
                   set(("make_manifest.py", "commit-standalone",
                        "vendor", ".gitmodules", ".travis.yml", ".travis-runtox.py")))
    with open("MANIFEST.in", "w") as f:
        for x in files:
            f.write("include %s\n" % x)

if __name__ == '__main__':
    main()
