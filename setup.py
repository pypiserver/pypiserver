#! /usr/bin/env python

from distutils.core import setup


def get_version():
    d = {}
    try:
        execfile("pypiserver/__init__.py", d, d)
    except (ImportError, RuntimeError):
        pass
    return d["__version__"]


setup(name="pypiserver",
      description="minimal pypi server",
      version=get_version(),
      packages=["pypiserver"],
      scripts=["pypi-server"],
      url="https://github.com/schmir/pypiserver",
      maintainer="Ralf Schmitt",
      maintainer_email="ralf@systemexit.de")
