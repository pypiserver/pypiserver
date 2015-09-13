#! /usr/bin/env python

"""generate a single file pypi-server script"""
from __future__ import unicode_literals

import os, zlib, base64, itertools
try:
    import cPickle
except ImportError:
    import pickle as cPickle

def find_files(path):
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            yield os.path.join(dirpath, f)

def myExecFile(file, g, l):
    try:
        execfile(file, g, l)
    except NameError:
        with open(file) as fd:
            txt = fd.read()
            exec(txt, g, l)

def get_version():
    d = {}
    try:
        myExecFile("pypiserver/__init__.py", d, d)
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

    try:
        data = str(data, encoding='ascii')
    except TypeError: # we were in PY2
        data = '%s' % data

    script = open("pypi-server-in.py").read()
    script = script.replace("@VERSION@", get_version())
    script = script.replace('@SOURCES@', data)
    dst = "pypi-server-standalone.py"
    open(dst, "wt").write(script)
    os.chmod(dst, 755)
    print("created %s"%dst)


if __name__ == '__main__':
    main()
