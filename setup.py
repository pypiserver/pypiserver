#! /usr/bin/env python

import sys, os
extrakw = {}

try:
    from setuptools import setup
    extrakw["use_2to3"] = True
except ImportError:
    if sys.version_info >= (3, 0):
        raise
    from distutils.core import setup


if sys.version_info >= (3, 0):
    exec("def do_exec(co, loc): exec(co, loc)\n")
else:
    exec("def do_exec(co, loc): exec co in loc\n")


def get_version():
    d = {}
    try:
        do_exec(open("pypiserver/__init__.py").read(), d)
    except (ImportError, RuntimeError):
        pass
    return d["__version__"]


def read_long_description():
    fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.rst")
    return open(fn).read()


setup(name="pypiserver",
      description="minimal pypi server",
      long_description = read_long_description(),
      version=get_version(),
      packages=["pypiserver"],
      scripts=["pypi-server"],
      url="https://github.com/schmir/pypiserver",
      maintainer="Ralf Schmitt",
      maintainer_email="ralf@systemexit.de",
      classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: BSD License",
        "License :: OSI Approved :: zlib/libpng License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.0",
        "Programming Language :: Python :: 3.1",
        "Programming Language :: Python :: 3.2",
        "Topic :: Software Development :: Build Tools",
        "Topic :: System :: Software Distribution"],
      **extrakw)
