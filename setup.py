#! /usr/bin/env python

import sys, os

try:
    from setuptools import setup
    extra = dict(entry_points={
            'paste.app_factory': ['main=pypiserver:paste_app_factory'],
            'console_scripts': ['pypi-server=pypiserver.core:main']
            })
except ImportError:
    from distutils.core import setup
    extra = dict(scripts=["pypi-server"])

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


setup(name="pypiserver",
      description="minimal pypi server",
      long_description=open("README.rst").read(),
      version=get_version(),
      packages=["pypiserver"],
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
        "Programming Language :: Python :: 3.3",
        "Topic :: Software Development :: Build Tools",
        "Topic :: System :: Software Distribution"],
      **extra)
