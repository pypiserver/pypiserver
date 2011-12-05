#! /usr/bin/env python

"""generate a single file pypi-server script"""

import os, zlib, cPickle, base64, glob


def get_version():
    d = {}
    try:
        execfile("pypiserver/__init__.py", d, d)
    except (ImportError, RuntimeError):
        pass
    return d["__version__"]


def main():
    name2src = {}
    for f in glob.glob("pypiserver/*.py"):
        k = f.replace('/', '.')[:-3]
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
