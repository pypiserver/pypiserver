#!/usr/bin/env python
"""Setup file for Pypiserver."""

from os import path
import sys

from setuptools import find_packages, setup


tests_require = ['pytest>=2.3', 'tox', 'twine', 'pip>=7',
                 'passlib>=1.6', 'webtest']
if sys.version_info == (2, 7):
    tests_require.append('mock')

setup_requires = ['setuptools', 'setuptools-git >= 0.3']
if sys.version_info >= (3, 5):
    setup_requires.append('wheel >= 0.25.0')  # earlier wheels fail in 3.5
else:
    setup_requires.append('wheel')


def get_version():
    """Execute just what is needed from _version.py to get the version."""
    fake_globals = {}
    v_file = path.abspath(
        path.join(path.dirname(__file__), 'pypiserver/_version.py')
    )
    with open(v_file) as vf:
        for ln in vf:
            if ln.startswith('__version__'):
                exec(ln, fake_globals)
    return fake_globals["__version__"]


setup(
    name="pypiserver",
    description="A minimal PyPI server for use with pip/easy_install.",
    long_description=open("README.rst").read(),
    version=get_version(),
    packages=find_packages(exclude=('tests', 'tests.*')),
    package_data={'pypiserver': ['welcome.html']},
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
    setup_requires=setup_requires,
    extras_require={
        'passlib': ['passlib>=1.6'],
        'cache': ['watchdog']
    },
    tests_require=tests_require,
    url="https://github.com/pypiserver/pypiserver",
    maintainer=("Kostis Anagnostopoulos <ankostis@gmail.com>"
                "Matthew Planchard <mplanchard@gmail.com>"),
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
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Build Tools",
        "Topic :: System :: Software Distribution"],
    zip_safe=True,
    entry_points={
        'paste.app_factory': ['main=pypiserver.paste:paste_app_factory'],
        'console_scripts': [
            'pypi-server=pypiserver.__main__:main',
            'pypiserver=pypiserver.__main__:main',
        ],
        'pypiserver.authenticators': [
            'htpasswd = '
            'pypiserver.plugins.authenticators.htpasswd:HtpasswdAuthenticator '
            '[passlib]',
            'no-auth = '
            'pypiserver.plugins.authenticators.no_auth:NoAuthAuthenticator'
        ]
    },
    options={
        'bdist_wheel': {'universal': True},
    },
    platforms=['any'],
)
