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


- [Quickstart: Installation and Usage](#Quickstart:-Installation-and-Usage)
  - [More details about *pypi-server run*](#More-details-about-pypi-server-run)
  - [More details about *pypi-server update*](#More-details-about-pypi-server-update)

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


1. Install **pypiserver** with this command

```shell
   pip install pypiserver                # Or: pypiserver[passlib,cache]
   mkdir ~/packages                      # Copy packages into this directory.
```
   See also [Alternative Installation methods]()

2. Copy some packages into your **~/packages** folder and then
   get your **pypiserver** up and running
```shell
   pypi-server run -p 8080 ~/packages &      # Will listen to all IPs.
```

3. From the client computer, type this
```shell
   # Download and install hosted packages.
   pip install --extra-index-url http://localhost:8080/simple/ ...

   # or
   pip install --extra-index-url http://localhost:8080 ...

   # Search hosted packages.
   pip search --index http://localhost:8080 ...

   # Note that pip search does not currently work with the /simple/ endpoint.
```

   See also [Client-side configurations]() for avoiding tedious typing.

4. Enter **pypi-server -h** in the cmd-line to print a detailed usage message

```shell
usage: pypi-server [-h] [-v] [--log-file FILE] [--log-stream STREAM]
                   [--log-frmt FORMAT] [--hash-algo HASH_ALGO]
                   [--backend {auto,simple-dir,cached-dir}] [--version]
                   {run,update} ...

start PyPI compatible package server serving packages from PACKAGES_DIRECTORY. If PACKAGES_DIRECTORY is not given on the command line, it uses the default ~/packages. pypiserver scans this directory recursively for packages. It skips packages and directories starting with a dot. Multiple package directories may be specified.

positional arguments:
  {run,update}
    run                 Run pypiserver, serving packages from
                        PACKAGES_DIRECTORY
    update              Handle updates of packages managed by pypiserver. By
                        default, a pip command to update the packages is
                        printed to stdout for introspection or pipelining. See
                        the `-x` option for updating packages directly.

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Enable verbose logging; repeat for more verbosity.
  --log-file FILE       Write logging info into this FILE, as well as to
                        stdout or stderr, if configured.
  --log-stream STREAM   Log messages to the specified STREAM. Valid values are
                        stdout, stderr, and none
  --log-frmt FORMAT     The logging format-string.  (see `logging.LogRecord`
                        class from standard python library)
  --hash-algo HASH_ALGO
                        Any `hashlib` available algorithm to use for
                        generating fragments on package links. Can be disabled
                        with one of (0, no, off, false).
  --backend {auto,simple-dir,cached-dir}
                        A backend implementation. Keep the default 'auto' to
                        automatically determine whether to activate caching or
                        not
  --version             show program's version number and exit

Visit https://github.com/pypiserver/pypiserver for more information
 

```
### More details about pypi server run
Enter **pypi-server run -h** in the cmd-line to print a detailed usage
```shell
usage: pypi-server run [-h] [-v] [--log-file FILE] [--log-stream STREAM]
                       [--log-frmt FORMAT] [--hash-algo HASH_ALGO]
                       [--backend {auto,simple-dir,cached-dir}] [--version]
                       [-p PORT] [-i HOST] [-a AUTHENTICATE]
                       [-P PASSWORD_FILE] [--disable-fallback]
                       [--fallback-url FALLBACK_URL]
                       [--health-endpoint HEALTH_ENDPOINT] [--server METHOD]
                       [-o] [--welcome HTML_FILE] [--cache-control AGE]
                       [--log-req-frmt FORMAT] [--log-res-frmt FORMAT]
                       [--log-err-frmt FORMAT]
                       [package_directory [package_directory ...]]

positional arguments:
  package_directory     The directory from which to serve packages.

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Enable verbose logging; repeat for more verbosity.
  --log-file FILE       Write logging info into this FILE, as well as to
                        stdout or stderr, if configured.
  --log-stream STREAM   Log messages to the specified STREAM. Valid values are
                        stdout, stderr, and none
  --log-frmt FORMAT     The logging format-string.  (see `logging.LogRecord`
                        class from standard python library)
  --hash-algo HASH_ALGO
                        Any `hashlib` available algorithm to use for
                        generating fragments on package links. Can be disabled
                        with one of (0, no, off, false).
  --backend {auto,simple-dir,cached-dir}
                        A backend implementation. Keep the default 'auto' to
                        automatically determine whether to activate caching or
                        not
  --version             show program's version number and exit
  -p PORT, --port PORT  Listen on port PORT (default: 8080)
  -i HOST, -H HOST, --interface HOST, --host HOST
                        Listen on interface INTERFACE (default: 0.0.0.0)
  -a AUTHENTICATE, --authenticate AUTHENTICATE
                        Comma-separated list of (case-insensitive) actions to
                        authenticate (options: download, list, update;
                        default: update).
                         
                         Any actions not specified are not authenticated, so
                         to authenticate downloads and updates, but allow
                         unauthenticated viewing of the package list, you would
                         use:
                         
                          pypi-server -a 'download, update' -P
                          ./my_passwords.htaccess
                         
                        To disable authentication, use:
                         
                          pypi-server -a . -P .
                         
                        See the `-P` option for configuring users and
                        passwords.
                         
                        Note that when uploads are not protected, the
                        `register` command is not necessary, but `~/.pypirc`
                        still needs username and password fields, even if
                        bogus.
  -P PASSWORD_FILE, --passwords PASSWORD_FILE
                        Use an apache htpasswd file PASSWORD_FILE to set
                        usernames and passwords for authentication.
                         
                        To allow unauthorized access, use:
                         
                          pypi-server -a . -P .
                         
  --disable-fallback    Disable the default redirect to PyPI for packages not
                        found in the local index.
  --fallback-url FALLBACK_URL
                        Redirect to FALLBACK_URL for packages not found in the
                        local index.
  --health-endpoint HEALTH_ENDPOINT
                        Configure a custom liveness endpoint. It always
                        returns 200 Ok if the service is up. Otherwise, it
                        means that the service is not responsive.
  --server METHOD       Use METHOD to run the server. Valid values include
                        paste, cherrypy, twisted, gunicorn, gevent, wsgiref,
                        and auto. The default is to use "auto", which chooses
                        one of paste, cherrypy, twisted, or wsgiref.
  -o, --overwrite       Allow overwriting existing package files during
                        upload.
  --welcome HTML_FILE   Use the contents of HTML_FILE as a custom welcome
                        message on the home page.
  --cache-control AGE   Add "Cache-Control: max-age=AGE" header to package
                        downloads. Pip 6+ requires this for caching.AGE is
                        specified in seconds.
  --log-req-frmt FORMAT
                        A format-string selecting Http-Request properties to
                        log; set to '%s' to see them all.
  --log-res-frmt FORMAT
                        A format-string selecting Http-Response properties to
                        log; set to '%s' to see them all.
  --log-err-frmt FORMAT
                        A format-string selecting Http-Error properties to
                        log; set to '%s' to see them all.

```
### More details about pypi-server update
More details about **pypi-server update**

```shell
usage: pypi-server run [-h] [-v] [--log-file FILE] [--log-stream STREAM]
                       [--log-frmt FORMAT] [--hash-algo HASH_ALGO]
                       [--backend {auto,simple-dir,cached-dir}] [--version]
                       [-p PORT] [-i HOST] [-a AUTHENTICATE]
                       [-P PASSWORD_FILE] [--disable-fallback]
                       [--fallback-url FALLBACK_URL]
                       [--health-endpoint HEALTH_ENDPOINT] [--server METHOD]
                       [-o] [--welcome HTML_FILE] [--cache-control AGE]
                       [--log-req-frmt FORMAT] [--log-res-frmt FORMAT]
                       [--log-err-frmt FORMAT]
                       [package_directory [package_directory ...]]

positional arguments:
  package_directory     The directory from which to serve packages.

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Enable verbose logging; repeat for more verbosity.
  --log-file FILE       Write logging info into this FILE, as well as to
                        stdout or stderr, if configured.
  --log-stream STREAM   Log messages to the specified STREAM. Valid values are
                        stdout, stderr, and none
  --log-frmt FORMAT     The logging format-string.  (see `logging.LogRecord`
                        class from standard python library)
  --hash-algo HASH_ALGO
                        Any `hashlib` available algorithm to use for
                        generating fragments on package links. Can be disabled
                        with one of (0, no, off, false).
  --backend {auto,simple-dir,cached-dir}
                        A backend implementation. Keep the default 'auto' to
                        automatically determine whether to activate caching or
                        not
  --version             show program's version number and exit
  -p PORT, --port PORT  Listen on port PORT (default: 8080)
  -i HOST, -H HOST, --interface HOST, --host HOST
                        Listen on interface INTERFACE (default: 0.0.0.0)
  -a AUTHENTICATE, --authenticate AUTHENTICATE
                        Comma-separated list of (case-insensitive) actions to
                        authenticate (options: download, list, update;
                        default: update).
                         
                         Any actions not specified are not authenticated, so
                         to authenticate downloads and updates, but allow
                         unauthenticated viewing of the package list, you would
                         use:
                         
                          pypi-server -a 'download, update' -P
                          ./my_passwords.htaccess
                         
                        To disable authentication, use:
                         
                          pypi-server -a . -P .
                         
                        See the `-P` option for configuring users and
                        passwords.
                         
                        Note that when uploads are not protected, the
                        `register` command is not necessary, but `~/.pypirc`
                        still needs username and password fields, even if
                        bogus.
  -P PASSWORD_FILE, --passwords PASSWORD_FILE
                        Use an apache htpasswd file PASSWORD_FILE to set
                        usernames and passwords for authentication.
                         
                        To allow unauthorized access, use:
                         
                          pypi-server -a . -P .
                         
  --disable-fallback    Disable the default redirect to PyPI for packages not
                        found in the local index.
  --fallback-url FALLBACK_URL
                        Redirect to FALLBACK_URL for packages not found in the
                        local index.
  --health-endpoint HEALTH_ENDPOINT
                        Configure a custom liveness endpoint. It always
                        returns 200 Ok if the service is up. Otherwise, it
                        means that the service is not responsive.
  --server METHOD       Use METHOD to run the server. Valid values include
                        paste, cherrypy, twisted, gunicorn, gevent, wsgiref,
                        and auto. The default is to use "auto", which chooses
                        one of paste, cherrypy, twisted, or wsgiref.
  -o, --overwrite       Allow overwriting existing package files during
                        upload.
  --welcome HTML_FILE   Use the contents of HTML_FILE as a custom welcome
                        message on the home page.
  --cache-control AGE   Add "Cache-Control: max-age=AGE" header to package
                        downloads. Pip 6+ requires this for caching.AGE is
                        specified in seconds.
  --log-req-frmt FORMAT
                        A format-string selecting Http-Request properties to
                        log; set to '%s' to see them all.
  --log-res-frmt FORMAT
                        A format-string selecting Http-Response properties to
                        log; set to '%s' to see them all.
  --log-err-frmt FORMAT
                        A format-string selecting Http-Error properties to
                        log; set to '%s' to see them all.

```
## Client-Side Configurations
Always specifying the pypi url on the command line is a bit
cumbersome. Since **pypiserver** redirects **pip/easy_install** to the
**pypi.org** index if it doesn't have a requested package, it is a
good idea to configure them to always use your local pypi index.

### Configuring **pip**

For **pip** command this can be done by setting the environment variable
**[PIP_EXTRA_INDEX_URL](https://packaging.python.org/en/latest/guides/hosting-your-own-index/)** in your **.bashr/.profile/.zshrc**

```shell
export PIP_EXTRA_INDEX_URL=http://localhost:8080/simple/
```

or by adding the following lines to **~/.pip/pip.conf**

```shell
[global]
extra-index-url = http://localhost:8080/simple/
```

Note

If you have installed **pypiserver** on a remote url without *https*
you will receive an "untrusted" warning from *pip*, urging you to append
the **--trusted-host** option.  You can also include this option permanently
in your configuration-files or environment variables.
