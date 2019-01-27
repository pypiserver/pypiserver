#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from os.path import dirname, join

from setuptools import find_packages, setup


INFO_FILE = "src/pypiserver/info.py"
REQS_FILE = "requirements/run.txt"


def read(path: str, encoding: str = "utf8") -> str:
    """Read a file and return the text."""
    from os import listdir
    from os.path import abspath
    mydir = abspath(dirname(__file__))
    print(listdir(mydir))
    return open(join(dirname(__file__), path), encoding=encoding).read()


def get_info():
    """Get package info."""
    info_txt = read(INFO_FILE)
    ret = {}
    exec(info_txt, ret)  # nosec
    return ret


def get_requirements():
    """Get package requirements."""
    req_txt = read(REQS_FILE)
    return req_txt.splitlines()


INFO = get_info()


setup(
    name=INFO["__pkg_name__"],
    version=INFO["__full_version__"],
    license=INFO["__license__"],
    description=INFO["__short_description__"],
    long_description=INFO["__long_description__"],
    author=INFO["__author__"],
    author_email=INFO["__author_email__"],
    url=INFO["__url__"],
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=get_requirements(),
    extras_require={
        # eg:
        #   'rst': ['docutils>=0.11'],
        #   ':python_version=="2.6"': ['argparse'],
    },
    entry_points={},
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3 :: Only"
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Build Tools",
        "Topic :: System :: Software Distribution",
    ],
    keywords=[
        "packaging",
        "pypi",
        "pip",
        "packages",
        "download",
        "package server",
        "server",
        "distribute",
        "distribution",
    ],
)
