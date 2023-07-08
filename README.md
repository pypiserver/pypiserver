![pypi server logo](docs/__resources__/pypiserver_logo.png)

[**pypiserver - minimal PyPI server for use with pip/easy_install**]()

[![pypi badge](https://img.shields.io/badge/pypi-v1.5.1-blue.svg)](https://shields.io/)
![ci workflow](https://github.com/pypiserver/pypiserver/actions/workflows/ci.yml/badge.svg)
[![Generic badge](https://img.shields.io/badge/python-3.6|3.7|3.8+-blue.svg)](https://shields.io/)
[![Generic badge](https://img.shields.io/badge/license-MIT|zlib/libpng-blue.svg)](https://shields.io/)


| name         | description                                                                                                                                                                                                                                      |
|:-------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Version      | 1.5.1                                                                                                                                                                                                                                            |
| Date:        | 2022-10-18                                                                                                                                                                                                                                       |
| Source       | https://github.com/pypiserver/pypiserver                                                                                                                                                                                                         |
| PyPI         | https://pypi.org/project/pypiserver/                                                                                                                                                                                                             |
| Tests        | https://github.com/pypiserver/pypiserver/actions                                                                                                                                                                                                 |
| Maintainers  | Kostis Anagnostopoulos <ankostis@gmail.com>, Matthew Planchard <mplanchard@gmail.com>,  Dmitrii Orlov <dmtree.dev@yahoo.com>,  **Someone new?** We are looking for new maintainers! [#397](https://github.com/pypiserver/pypiserver/issues/397)  |
| License      | zlib/libpng + MIT                                                                                                                                                                                                                                |
| Community    | https://pypiserver.zulipchat.com                                                                                                                                                                                                                 |

Chat with us on [Zulip](https://pypiserver.zulipchat.com)

**pypiserver** is a minimal [PyPI](https://pypi.org/) compatible server for **pip** or **easy_install**.
It is based on [bottle](http://bottlepy.org/) and serves packages from regular directories.
Wheels, bdists, eggs and accompanying PGP-signatures can be uploaded
either with **pip**, **setuptools**, **twine**, **pypi-uploader**, or simply copied
with **scp**.

Note
The official software powering [PyPI](https://pypi.org/) is 
[Warehouse](https://github.com/pypa/warehouse/). However, 
[Warehouse](https://github.com/pypa/warehouse/)
is fairly specialized to be **pypi.org**'s own software, and should not
be used in other contexts. In particular, it does not officially support
being used as a custom package index by users wishing to serve their own
packages.

**pypiserver** implements the same interfaces as , allowing
standard Python packaging tooling such as **pip** and **twine** to
interact with it as a package index just as they would with [PyPI](https://pypi.org/), while
making it much easier to get a running index server.

# pypiserver 

Table of Contents 
pypiserver - minimal PyPI server for use with pip/easy_install

- [Quickstart: Installation and Usage](#Quickstart-Installation-and-Usage)

## Quickstart: Installation and Usage
**pypiserver** works with Python 3.6+ and PyPy3.

Older Python versions may still work, but they are not tested.

For legacy Python versions, use **pypiserver-1.x** series. Note that these are
not officially supported, and will not receive bugfixes or new features.

Tip

The commands below work on a unix-like operating system with a posix shell.
The **'~'** character expands to user's home directory.

If you're using Windows, you'll have to use their "Windows counterparts".
The same is true for the rest of this documentation.

