#! /usr/bin/env python

"""generate a single file pypi-server script"""

import os, zlib, cPickle, base64, itertools


def find_files(path):
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            yield os.path.join(dirpath, f)


def get_version():
    d = {}
    try:
        execfile("pypiserver/__init__.py", d, d)
    except (ImportError, RuntimeError):
        pass
    return d["__version__"]


def main():
    name2src = {}

    for f in itertools.chain(find_files("pypiserver"),
                             find_files("vendor")):
        if not f.endswith(".py"):
            continue

        k = f.replace('/', '.')[:-3]
        if k.startswith("vendor."):
            k = k[len("vendor."):]
        name2src[k] = open(f).read()

    data = cPickle.dumps(name2src, 2)
    data = zlib.compress(data, 9)
    data = base64.encodestring(data)

    data = '%s' % (data)

    script = open("pypi-server-in.py").read()
    script = script.replace("@VERSION@", get_version())
    script = script.replace('@SOURCES@', data)
    dst = "pypi-server-standalone.py"
    open(dst, "w").write(script)
    os.chmod(dst, 0755)
    print "created", dst


if __name__ == '__main__':
    main()
