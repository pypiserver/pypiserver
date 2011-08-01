#! /usr/bin/env python

import os
from distutils.core import setup


def get_version():
    d = {}
    try:
        execfile("pypiserver/__init__.py", d, d)
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
        "Programming Language :: Python :: 2.5",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development :: Build Tools",
        "Topic :: System :: Software Distribution"])
