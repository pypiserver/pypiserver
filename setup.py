#! /usr/bin/env python

import sys

from setuptools import setup

if sys.version_info >= (3, 0):
    exec("def do_exec(co, loc): exec(co, loc)\n")
else:
    exec("def do_exec(co, loc): exec co in loc\n")

tests_require = [
    "pytest>=2.3",
    "tox",
    "twine",
    "pip>=7",
    "passlib>=1.6",
    "webtest",
]
if sys.version_info == (2, 7):
    tests_require.append("mock")

setup_requires = ["setuptools", "setuptools-git >= 0.3"]
if sys.version_info >= (3, 5):
    setup_requires.append("wheel >= 0.25.0")  # earlier wheels fail in 3.5
else:
    setup_requires.append("wheel")


def get_version():
    d = {}
    try:
        do_exec(open("pypiserver/__init__.py").read(), d)  # @UndefinedVariable
    except (ImportError, RuntimeError):
        pass
    return d["__version__"]


setup(
    name="pypiserver",
    description="A minimal PyPI server for use with pip/easy_install.",
    long_description=open("README.rst").read(),
    version=get_version(),
    packages=["pypiserver"],
    package_data={"pypiserver": ["welcome.html"]},
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
    setup_requires=setup_requires,
    extras_require={"passlib": ["passlib>=1.6"], "cache": ["watchdog"]},
    tests_require=tests_require,
    url="https://github.com/pypiserver/pypiserver",
    maintainer=(
        "Kostis Anagnostopoulos <ankostis@gmail.com>"
        "Matthew Planchard <mplanchard@gmail.com>"
    ),
    maintainer_email="ankostis@gmail.com",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: BSD License",
        "License :: OSI Approved :: zlib/libpng License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Build Tools",
        "Topic :: System :: Software Distribution",
    ],
    zip_safe=True,
    entry_points={
        "paste.app_factory": ["main=pypiserver:paste_app_factory"],
        "console_scripts": ["pypi-server=pypiserver.__main__:main"],
    },
    options={"bdist_wheel": {"universal": True}},
    platforms=["any"],
)
