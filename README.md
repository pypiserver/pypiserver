![pypi server logo](docs/__resources__/pypiserver_logo.png)

# [**pypiserver - minimal PyPI server for use with pip/easy_install**](#pypiserver)

[![pypi badge](https://img.shields.io/pypi/v/pypiserver.svg)](https://shields.io/)
[![ci workflow](https://github.com/pypiserver/pypiserver/actions/workflows/ci.yml/badge.svg)](https://github.com/pypiserver/pypiserver/actions/workflows/ci.yml)
[![Generic badge](https://img.shields.io/badge/python-3.6%7C3.7%7C3.8+-blue.svg)](https://pypi.org/project/pypiserver/)
[![Generic badge](https://img.shields.io/badge/license-MIT%7Czlib/libpng-blue.svg)](https://raw.githubusercontent.com/pypiserver/pypiserver/main/LICENSE.txt)

| name        | description                                                                                                                                                                                                                                                                                                             |
| :---------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Version     | 2.3.0                                                                                                                                                                                                                                                                                                                   |
| Date:       | 2024-11-23                                                                                                                                                                                                                                                                                                              |
| Source      | <https://github.com/pypiserver/pypiserver>                                                                                                                                                                                                                                                                              |
| PyPI        | <https://pypi.org/project/pypiserver/>                                                                                                                                                                                                                                                                                  |
| Tests       | <https://github.com/pypiserver/pypiserver/actions>                                                                                                                                                                                                                                                                      |
| Maintainers | [`@ankostis`](https://github.com/ankostis), [`@mplanchard`](https://github.com/mplanchard), [`@dee-me-tree-or-love`](https://github.com/dee-me-tree-or-love), [`@pawamoy`](https://github.com/pawamoy), **Someone new?** *We are open for new maintainers! [#397](https://github.com/pypiserver/pypiserver/issues/397)* |
| License     | zlib/libpng + MIT                                                                                                                                                                                                                                                                                                       |
| Community   | <https://pypiserver.zulipchat.com>                                                                                                                                                                                                                                                                                      |

> [!TIP]
> Reach out in [**Discussions**](https://github.com/pypiserver/pypiserver/discussions),
> or chat with us on [**Zulip**](https://pypiserver.zulipchat.com)

**pypiserver** is a minimal [PyPI](https://pypi.org/) compatible server for **pip** or **easy_install**.
It is based on [bottle](http://bottlepy.org/) and serves packages from regular directories.
Wheels, bdists, eggs and accompanying PGP-signatures can be uploaded
either with **pip**, **setuptools**, **twine**, **pypi-uploader**, or simply copied
with **scp**.

> [!Note]
> The official software powering [PyPI](https://pypi.org/) is
> [Warehouse](https://github.com/pypa/warehouse/). However,
> [Warehouse](https://github.com/pypa/warehouse/)
> is fairly specialized to be **pypi.org**'s own software, and should not
> be used in other contexts. In particular, it does not officially support
> being used as a custom package index by users wishing to serve their own
> packages.

**pypiserver** implements the same interfaces as [PyPI](https://pypi.org/), allowing
standard Python packaging tooling such as **pip** and **twine** to
interact with it as a package index just as they would with [PyPI](https://pypi.org/), while
making it much easier to get a running index server.

# pypiserver

Table of Contents

- [**pypiserver - minimal PyPI server for use with pip/easy_install**](#pypiserver---minimal-pypi-server-for-use-with-pipeasy_install)
- [pypiserver](#pypiserver)
  - [Quickstart Installation and Usage](#quickstart-installation-and-usage)
    - [More details about pypi server run](#more-details-about-pypi-server-run)
    - [More details about pypi-server update](#more-details-about-pypi-server-update)
  - [Client-Side Configurations](#client-side-configurations)
    - [Configuring pip](#configuring-pip)
    - [Configuring easy_install](#configuring-easy_install)
    - [Uploading Packages Remotely](#uploading-packages-remotely)
      - [Apache Like Authentication (htpasswd)](#apache-like-authentication-htpasswd)
      - [Upload with setuptools](#upload-with-setuptools)
      - [Upload with twine](#upload-with-twine)
  - [Using the Docker Image](#using-the-docker-image)
  - [Alternative Installation Methods](#alternative-installation-methods)
    - [Installing the Very Latest Version](#installing-the-very-latest-version)
  - [Recipes](#recipes)
    - [Managing the Package Directory](#managing-the-package-directory)
    - [Serving Thousands of Packages](#serving-thousands-of-packages)
    - [Managing Automated Startup](#managing-automated-startup)
      - [Running As a systemd Service](#running-as-a-systemd-service)
      - [Launching through supervisor](#launching-through-supervisor)
      - [Running As a service with NSSM](#running-as-a-service-with-nssm)
    - [Using a Different WSGI Server](#using-a-different-wsgi-server)
      - [Apache](#apache)
      - [gunicorn](#gunicorn)
      - [paste](#paste)
    - [Behind a Reverse Proxy](#behind-a-reverse-proxy)
      - [Nginx](#nginx)
      - [Supporting HTTPS](#supporting-https)
      - [Traefik](#traefik)
    - [Utilizing the API](#utilizing-the-api)
      - [Using Ad-Hoc Authentication Providers](#using-ad-hoc-authentication-providers)
    - [Use with MicroPython](#use-with-micropython)
    - [Custom Health Check Endpoint](#custom-health-check-endpoint)
      - [Configure a custom health endpoint by CLI arguments](#configure-a-custom-health-endpoint-by-cli-arguments)
      - [Configure a custom health endpoint by script](#configure-a-custom-health-endpoint-by-script)
  - [Sources](#sources)
  - [Known Limitations](#known-limitations)
  - [Similar Projects](#similar-projects)
    - [Unmaintained or archived](#unmaintained-or-archived)
  - [Related Software](#related-software)
- [Licensing](#licensing)

## Quickstart Installation and Usage

**pypiserver** works with Python 3.6+ and PyPy3.

Older Python versions may still work, but they are not tested.

For legacy Python versions, use **pypiserver-1.x** series. Note that these are
not officially supported, and will not receive bugfixes or new features.

> [!TIP]
>
> The commands below work on a unix-like operating system with a posix shell.
> The **'~'** character expands to user's home directory.

If you're using Windows, you'll have to use their "Windows counterparts".
The same is true for the rest of this documentation.

1. Install **pypiserver** with this command

   ```shell
   pip install pypiserver                # Or: pypiserver[passlib,cache]
   mkdir ~/packages                      # Copy packages into this directory.
   ```

   > [!TIP]
   > See also [Alternative Installation methods](#alternative-installation-methods)

1. Copy some packages into your **~/packages** folder and then
   get your **pypiserver** up and running

   ```shell
   pypi-server run -p 8080 ~/packages &      # Will listen to all IPs.
   ```

1. From the client computer, type this

   ```shell
   # Download and install hosted packages.
   pip install --extra-index-url http://localhost:8080/simple/ ...

   # or
   pip install --extra-index-url http://localhost:8080 ...

   # Search hosted packages.
   pip search --index http://localhost:8080 ...

   # Note that pip search does not currently work with the /simple/ endpoint.
   ```

   > [!TIP]
   > See also [Client-side configurations](#client-side-configurations) for avoiding tedious typing.

1. Enter **pypi-server -h** in the cmd-line to print a detailed usage message

   <!-- NB: this text should be updated if the help message changes -->

   ```text
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

<!-- NB: this text should be updated if the help message changes -->

```text
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

```text
usage: pypi-server update [-h] [-v] [--log-file FILE] [--log-stream STREAM]
                          [--log-frmt FORMAT] [--hash-algo HASH_ALGO]
                          [--backend {auto,simple-dir,cached-dir}] [--version]
                          [-x] [-d DOWNLOAD_DIRECTORY] [-u]
                          [--blacklist-file IGNORELIST_FILE]
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
  --log-frmt FORMAT     The logging format-string. (see `logging.LogRecord`
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
  -x, --execute         Execute the pip commands rather than printing to
                        stdout
  -d DOWNLOAD_DIRECTORY, --download-directory DOWNLOAD_DIRECTORY
                        Specify a directory where packages updates will be
                        downloaded. The default behavior is to use the
                        directory which contains the package being updated.
  -u, --allow-unstable  Allow updating to unstable versions (alpha, beta, rc,
                        dev, etc.)
  --blacklist-file IGNORELIST_FILE, --ignorelist-file IGNORELIST_FILE
                        Don't update packages listed in this file (one package
                        name per line, without versions, '#' comments
                        honored). This can be useful if you upload private
                        packages into pypiserver, but also keep a mirror of
                        public packages that you regularly update. Attempting
                        to pull an update of a private package from `pypi.org`
                        might pose a security risk - e.g. a malicious user
                        might publish a higher version of the private package,
                        containing arbitrary code.
```

## Client-Side Configurations

Always specifying the pypi url on the command line is a bit
cumbersome. Since **pypiserver** redirects **pip/easy_install** to the
**pypi.org** index if it doesn't have a requested package, it is a
good idea to configure them to always use your local pypi index.

### Configuring pip

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

> [!NOTE]
>
> If you have installed **pypiserver** on a remote url without *https*
> you will receive an "untrusted" warning from *pip*, urging you to append
> the **--trusted-host** option. You can also include this option permanently
> in your configuration-files or environment variables.

### Configuring easy_install

For **easy_install** command you may set the following configuration in
**~/.pydistutils.cfg**

```shell
[easy_install]
index_url = http://localhost:8080/simple/
```

### Uploading Packages Remotely

Instead of copying packages directly to the server's folder (i.e. with **scp**),
you may use python tools for the task, e.g. **python setup.py upload**.
In that case, **pypiserver** is responsible for authenticating the upload-requests.

> [!NOTE]
>
> We strongly advise to ***password-protect*** your uploads!

It is possible to disable authentication for uploads (e.g. in intranets).
To avoid lazy security decisions, read help for **-P** and **-a** options.

#### Apache Like Authentication (htpasswd)

1. First make sure you have the **passlib** module installed (note that
   **passlib>=1.6** is required), which is needed for parsing the Apache
   *htpasswd* file specified by the **-P**, **--passwords** option
   (see next steps)

   ```shell
       pip install passlib
   ```

1. Create the Apache **htpasswd** file with at least one user/password pair
   with this command (you'll be prompted for a password)

   ```shell
       htpasswd -sc htpasswd.txt <some_username>
   ```

> [!TIP]
>
> Read this [SO](http://serverfault.com/questions/152950/how-to-create-and-edit-htaccess-and-htpasswd-locally-on-my-computer-and-then-u)
> question for running `htpasswd` cmd under *Windows*
> or if you have bogus passwords that you don't care because they are for
> an internal service (which is still "bad", from a security perspective...)
> you may use this [public service](http://www.htaccesstools.com/htpasswd-generator/)

<!-- 2 tips separately -->

> [!TIP]
>
> When accessing pypiserver via the api, alternate authentication
> methods are available via the **auther** config flag. Any callable
> returning a boolean can be passed through to the pypiserver config in
> order to provide custom authentication. For example, to configure
> pypiserver to authenticate using the [python-pam](https://pypi.org/project/python-pam/)
>
> ```shell
>     import pam
>     pypiserver.default_config(auther=pam.authenticate)
> ```

Please see [`Using Ad-hoc authentication providers`](#using-ad-hoc-authentication-providers) for more information.

1. You need to restart the server with the **-P** option only once
   (but user/password pairs can later be added or updated on the fly)

   ```shell
       ./pypi-server run -p 8080 -P htpasswd.txt ~/packages &
   ```

#### Upload with setuptools

1. On client-side, edit or create a **~/.pypirc** file with a similar content:

   ```shell
       [distutils]
       index-servers =
         pypi
         local

       [pypi]
       username:<your_pypi_username>
       password:<your_pypi_passwd>

       [local]
       repository: http://localhost:8080
       username: <some_username>
       password: <some_passwd>
   ```

1. Then from within the directory of the python-project you wish to upload,
   issue this command:

   ```shell
       python setup.py sdist upload -r local
   ```

#### Upload with twine

To avoid storing you passwords on disk, in clear text, you may either:

- use the **register** *setuptools*'s command with the **-r** option,
  like that

  ```shell
    python setup.py sdist register -r local upload -r local
  ```

- use *twine* library, which
  breaks the procedure in two steps. In addition, it supports signing
  your files with PGP-Signatures and uploading the generated *.asc* files
  to **pypiserver**::

  ```shell
    twine upload -r local --sign -identity user_name ./foo-1.zip
  ```

## Using the Docker Image

Starting with version 1.2.5, official Docker images will be built for each
push to `main`, each dev, alpha, or beta release, and each final release.
The most recent full release will always be available under the tag **latest**,
and the current `main` branch will always be available under the tag
**unstable**.

You can always check to see what tags are currently available at our
[*Docker Repo*](https://hub.docker.com/r/pypiserver/pypiserver/tags/).

To run the most recent release of **pypiserver** with Docker, simply

```shell
    docker run pypiserver/pypiserver:latest run
```

This starts **pypiserver** serving packages from the **/data/packages**
directory inside the container, listening on the container port 8080.

The container takes all the same arguments as the normal **pypi-server**
executable, with the exception of the internal container port (**-p**),
which will always be 8080.

Of course, just running a container isn't that interesting. To map
port 80 on the host to port 8080 on the container::

```shell
    docker run -p 80:8080 pypiserver/pypiserver:latest run
```

You can now access your **pypiserver** at **localhost:80** in a web browser.

To serve packages from a directory on the host, e.g. **~/packages**

```shell
    docker run -p 80:8080 -v ~/packages:/data/packages pypiserver/pypiserver:latest run
```

To authenticate against a local **.htpasswd** file::

```shell
    docker run -p 80:8080 -v ~/.htpasswd:/data/.htpasswd pypiserver/pypiserver:latest run -P .htpasswd packages
```

You can also specify **pypiserver** to run as a Docker service using a
composefile. An example composefile is provided as
[`docker-compose.yaml`](./docker-compose.yml)

## Alternative Installation Methods

When trying the methods below, first use the following command to check whether
previous versions of **pypiserver** already exist, and (optionally) uninstall them::

```shell
# VERSION-CHECK: Fails if not installed.
pypi-server --version

# UNINSTALL: Invoke again until it fails.
pip uninstall pypiserver
```

### Installing the Very Latest Version

In case the latest version in *pypi* is a pre-release, you have to use
*pip*'s *--pre* option. And to update an existing installation combine it
with `--ignore-installed`

```shell
pip install pypiserver --pre -I
```

You can even install the latest **pypiserver** directly from *github* with the
following command, assuming you have *git* installed on your **PATH**

```shell
pip install git+git://github.com/pypiserver/pypiserver.git
```

## Recipes

### Managing the Package Directory

The **pypi-server** command has the **update** command that searches for updates of
available packages. It scans the package directory for available
packages and searches on pypi.org for updates. Without further
options **pypi-server update** will just print a list of commands which must
be run in order to get the latest version of each package. Output
looks like:

```shell
$ ./pypi-server update 
checking 106 packages for newer version

.........u.e...........e..u.............
.....e..............................e...
..........................

no releases found on pypi for PyXML, Pymacs, mercurial, setuptools

# update raven from 1.4.3 to 1.4.4
pip -q install --no-deps  --extra-index-url https://pypi.org/simple/ -d /home/ralf/packages/mirror raven==1.4.4

# update greenlet from 0.3.3 to 0.3.4
pip -q install --no-deps  --extra-index-url https://pypi.org/simple/ -d /home/ralf/packages/mirror greenlet==0.3.4
```

It first prints for each package a single character after checking the
available versions on pypi. A dot(.) means the package is up-to-date, **'u'**
means the package can be updated and **'e'** means the list of releases on
pypi is empty. After that it shows a *pip* command line which can be used
to update a one package. Either copy and paste that or run
**pypi-server update -x** in order to really execute those commands. You need
to have *pip* installed for that to work however.

Specifying an additional **-u** option will also allow alpha, beta and
release candidates to be downloaded. Without this option these
releases won't be considered.

### Serving Thousands of Packages

> [!IMPORTANT]
> By default, **pypiserver** scans the entire packages directory each time an
> incoming HTTP request occurs. This isn't a problem for a small number of
> packages, but causes noticeable slow-downs when serving thousands of packages.

If you run into this problem, significant speedups can be gained by enabling
pypiserver's directory caching functionality. The only requirement is to
install the **watchdog** package, or it can be installed during **pypiserver**
installation, by specifying the **cache** extras option::

```shell
pip install pypiserver[cache]
```

Additional speedups can be obtained by using your webserver's builtin
caching functionality. For example, if you are using `nginx` as a
reverse-proxy as described below in `Behind a reverse proxy`, you can
easily enable caching. For example, to allow nginx to cache up to
10 gigabytes of data for up to 1 hour::

```shell
proxy_cache_path /data/nginx/cache
                  levels=1:2
                  keys_zone=pypiserver_cache:10m
                  max_size=10g
                  inactive=60m
                  use_temp_path=off;

server {
    # ...
    location / {
        proxy_cache pypiserver_cache;
        proxy_pass http://localhost:8080;
    }
}
```

> [!TIP]
> Using webserver caching is especially helpful if you have high request
> volume. Using nginx caching, a real-world pypiserver installation was
> able to easily support over 1000 package downloads/min at peak load.

### Managing Automated Startup

There are a variety of options for handling the automated starting of
pypiserver upon system startup. Two of the most common are *systemd* and
*supervisor* for linux systems. For windows creating services with scripts isn't
an easy task without a third party tool such as *NSSM*.

#### Running As a systemd Service

**systemd** is installed by default on most modern Linux systems and as such,
it is an excellent option for managing the pypiserver process. An example
config file for **systemd** can be seen below

```shell
[Unit]
Description=A minimal PyPI server for use with pip/easy_install.
After=network.target

[Service]
Type=simple
# systemd requires absolute path here too.
PIDFile=/var/run/pypiserver.pid
User=www-data
Group=www-data

ExecStart=/usr/local/bin/pypi-server run -p 8080 -a update,download --log-file /var/log/pypiserver.log -P /etc/nginx/.htpasswd /var/www/pypi
ExecStop=/bin/kill -TERM $MAINPID
ExecReload=/bin/kill -HUP $MAINPID
Restart=always

WorkingDirectory=/var/www/pypi

TimeoutStartSec=3
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Adjusting the paths and adding this file as **pypiserver.service** into your
**systemd/system** directory will allow management of the pypiserver process with
**systemctl**, e.g. **systemctl start pypiserver**.

More useful information about *systemd* can be found at
<https://www.digitalocean.com/community/tutorials/how-to-use-systemctl-to-manage-systemd-services-and-units>

#### Launching through supervisor

[supervisor](http://supervisord.org/) has the benefit of being a pure python
package and as such, it provides excellent cross-platform support for process
management. An example configuration file for **supervisor** is given below

```shell
[program:pypi]
command=/home/pypi/pypi-venv/bin/pypi-server run -p 7001 -P /home/pypi/.htpasswd /home/pypi/packages
directory=/home/pypi
user=pypi
autostart=true
autorestart=true
stderr_logfile=/var/log/pypiserver.err.log
stdout_logfile=/var/log/pypiserver.out.log
```

From there, the process can be managed via **supervisord** using **supervisorctl**.

#### Running As a service with NSSM

For Windows download [NSSM](https://nssm.cc/) from <https://nssm.cc> unzip to a
desired location such as Program Files. Decide whether you are going
to use `win32` or `win64`, and add that `exe` to environment `PATH`.

Create a start_pypiserver.bat

```shell
pypi-server run -p 8080 C:\Path\To\Packages &
```

> [!TIP]
> Test the batch file by running it first before creating the service.
> Make sure you can access the server remotely, and install packages. If you can,
> proceed, if not troubleshoot until you can. This will ensure you know the server
> works, before adding NSSM into the mix.

From the command prompt

```shell
nssm install pypiserver
```

This command will launch a NSSM gui application

```shell
Path: C:\Path\To\start_pypiserver.bat
Startup directory: Auto generates when selecting path
Service name: pypiserver
```

There are more tabs, but that is the basic setup. If the service needs to be running with a certain
login credentials, make sure you enter those credentials in the logon tab.

Start the service

```shell
nssm start pypiserver
```

> [!TIP]
> Other useful commands
>
> ```shell
> nssm --help
> nssm stop <servicename>
> nssm restart <servicename>
> nssm status <servicename>
> ```
>
> For detailed information please visit <https://nssm.cc>

### Using a Different WSGI Server

- The **bottle** web-server which supports many WSGI-servers, among others,
  **paste**, **cherrypy**, **twisted** and **wsgiref** (part of Python); you select
  them using the **--server** flag.

- You may view all supported WSGI servers using the following interactive code

  ```python
  >>> from pypiserver import bottle
  >>> list(bottle.server_names.keys())
  ['cgi', 'gunicorn', 'cherrypy', 'eventlet', 'tornado', 'geventSocketIO',
  'rocket', 'diesel', 'twisted', 'wsgiref', 'fapws3', 'bjoern', 'gevent',
  'meinheld', 'auto', 'aiohttp', 'flup', 'gae', 'paste', 'waitress']
  ```

- If none of the above servers matches your needs, invoke just the
  **pypiserver:app()** method which returns the internal WSGI-app WITHOUT
  starting-up a server - you may then send it to any WSGI server you like.
  Read also the [Utilizing the API](#utilizing-the-api) section.

- Some examples are given below - you may find more details in [bottle
  site](http://bottlepy.org/docs/dev/deployment.html#switching-the-server-backend%3E).

#### Apache

To use your *Apache2* with **pypiserver**, prefer to utilize **mod_wsgi** as
explained in [bottle's documentation](http://bottlepy.org/docs/dev/deployment.html#apache-mod-wsgi%3E).

> [!NOTE]
> If you choose instead to go with **mod_proxy**, mind that you may bump into problems
> with the prefix-path (see [#155](https://github.com/pypiserver/pypiserver/issues/155%3E)).

1. Adapt and place the following *Apache* configuration either into top-level scope,
   or inside some **`<VirtualHost>`** (contributed by Thomas Waldmann):

   ```shell
   WSGIScriptAlias   /     /yoursite/wsgi/pypiserver-wsgi.py
   WSGIDaemonProcess       pypisrv user=pypisrv group=pypisrv umask=0007 \
                           processes=1 threads=5 maximum-requests=500 \
                           display-name=wsgi-pypisrv inactivity-timeout=300
   WSGIProcessGroup        pypisrv
   WSGIPassAuthorization On    # Required for authentication (https://github.com/pypiserver/pypiserver/issues/288)

   <Directory /yoursite/wsgi >
       Require all granted
   </Directory>
   ```

   or if using older **Apache < 2.4**, substitute the last part with this::

   ```shell
   <Directory /yoursite/wsgi >
       Order deny,allow
       Allow from all
   </Directory>
   ```

1. Then create the **/yoursite/cfg/pypiserver.wsgi** file and make sure that
   the **user** and **group** of the **WSGIDaemonProcess** directive
   (**pypisrv:pypisrv** in the example) have the read permission on it

   ```python

   import pypiserver

   conf = pypiserver.default_config(
       root =          "/yoursite/packages",
       password_file = "/yoursite/htpasswd", )
   application = pypiserver.app(**conf)

   ```

   > [!TIP]
   > If you have installed **pypiserver** in a virtualenv, follow **mod_wsgi**'s
   > [instructions](http://modwsgi.readthedocs.io/en/develop/user-guides/virtual-environments.html)
   > and prepend the python code above with the following
   >
   > ```python
   > import site
   >
   > site.addsitedir('/yoursite/venv/lib/pythonX.X/site-packages')
   > ```

<!-- tip and a note separately -->

> [!NOTE]
> For security reasons, notice that the **Directory** directive grants access
> to a directory holding the **wsgi** start-up script, alone; nothing else.

<!-- 2 notes separately -->

> [!NOTE]
> To enable HTTPS support on Apache, configure the directive that contains the
> WSGI configuration to use SSL.

#### gunicorn

The following command uses **gunicorn** to start **pypiserver**

```shell
gunicorn -w4 'pypiserver:app(root="/home/ralf/packages")'
```

or when using multiple roots

```shell
gunicorn -w4 'pypiserver:app(root=["/home/ralf/packages", "/home/ralf/experimental"])'
```

#### paste

[paste](http://pythonpaste.org) allows to run multiple WSGI applications
under different URL paths. Therefore, it is possible to serve different set
of packages on different paths.

The following example **paste.ini** could be used to serve stable and
unstable packages on different paths

```shell
  [composite:main]
  use = egg:Paste#urlmap
  /unstable/ = unstable
  / = stable

  [app:stable]
  use = egg:pypiserver#main
  root = ~/stable-packages

  [app:unstable]
  use = egg:pypiserver#main
  root = ~/stable-packages
      ~/unstable-packages

  [server:main]
  use = egg:gunicorn#main
  host = 0.0.0.0
  port = 9000
  workers = 5
  accesslog = -
```

> [!NOTE]
> You need to install some more dependencies for this to work, like::
>
> ```shell
> pip install paste pastedeploy gunicorn pypiserver
> ```
>
> The server can then start with
>
> ```shell
> gunicorn_paster paste.ini
> ```

### Behind a Reverse Proxy

You can run **pypiserver** behind a reverse proxy as well.

#### Nginx

Extend your nginx configuration

```shell
upstream pypi {
  server              pypiserver.example.com:12345 fail_timeout=0;
}

server {
  server_name         myproxy.example.com;

  location / {
    proxy_set_header  Host $host:$server_port;
    proxy_set_header  X-Forwarded-Proto $scheme;
    proxy_set_header  X-Real-IP $remote_addr;
    proxy_pass        http://pypi;
  }
}
```

As of pypiserver 1.3, you may also use the `X-Forwarded-Host` header in your
reverse proxy config to enable changing the base URL. For example if you
want to host pypiserver under a particular path on your server

```shell
upstream pypi {
  server              localhost:8000;
}

server {
  location /pypi/ {
      proxy_set_header  X-Forwarded-Host $host:$server_port/pypi;
      proxy_set_header  X-Forwarded-Proto $scheme;
      proxy_set_header  X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header  X-Real-IP $remote_addr;
      proxy_pass        http://pypi;
  }
}
```

#### Supporting HTTPS

Using a reverse proxy is the preferred way of getting pypiserver behind
HTTPS. For example, to put pypiserver behind HTTPS on port 443, with
automatic HTTP redirection, using `nginx`

```shell
upstream pypi {
  server               localhost:8000;
}

server {
  listen              80 default_server;
  server_name         _;
  return              301 https://$host$request_uri;
}

server {
  listen              443 ssl;
  server_name         pypiserver.example.com;

  ssl_certificate     /etc/star.example.com.crt;
  ssl_certificate_key /etc/star.example.com.key;
  ssl_protocols       TLSv1 TLSv1.1 TLSv1.2;
  ssl_ciphers         HIGH:!aNULL:!MD5;

  location / {
    proxy_set_header  Host $host:$server_port;
    proxy_set_header  X-Forwarded-Proto $scheme;
    proxy_set_header  X-Real-IP $remote_addr;
    proxy_pass        http://pypi;
  }
}
```

> [!TIP]
> Please see [nginx's HTTPS docs for more details](http://nginx.org/en/docs/http/configuring_https_servers.html).
>
> Getting and keeping your certificates up-to-date can be simplified using,
> for example, using [certbot and letsencrypt](https://www.digitalocean.com/community/tutorials/how-to-secure-nginx-with-let-s-encrypt-on-ubuntu-18-04%3E).

#### Traefik

It is also possible to use [Traefik](https://docs.traefik.io/) to put pypiserver
behind HTTPS on port 443, with automatic HTTP redirection using Docker Compose.
Please see the provided
[docker-compose.yml](./docker-compose.yml)
example for more information.

### Utilizing the API

In order to enable ad-hoc authentication-providers or to use WSGI-servers
not supported by *bottle* out-of-the-box, you needed to launch **pypiserver**
via its API.

- The main entry-point for configuring **pypiserver** is the
  [pypiserver:app()](./pypiserver/__init__.py#L116)
  function. This function returns the internal WSGI-app that you my then
  send to any WSGI-server you like.

- To get all **pypiserver:app()** keywords and their explanations, read the
  function [pypiserver:default_config()](./pypiserver/__init__.py#L35)

- Finally, to fire-up a WSGI-server with the configured app, invoke
  the **bottle:run(app, host, port, server)** function.
  Note that **pypiserver** ships with its own copy of *bottle*; to use it,
  import it like that: **from pypiserver import bottle**

#### Using Ad-Hoc Authentication Providers

The **auther** keyword of **pypiserver:app()** function maybe set only using
the API. This can be any callable that returns a boolean when passed
the *username* and the *password* for a given request.

For example, to authenticate users based on the **/etc/passwd** file under Unix,
you may delegate such decisions to the [python-pam](https://pypi.org/project/python-pam/) library by following
these steps:

1. Ensure **python-pam** module is installed

   ```shell
   pip install python-pam
   ```

1. Create a python-script along these lines

   ```shell
   $ cat > pypiserver-start.py
   import pypiserver
   from pypiserver import bottle
   import pam
   app = pypiserver.app(root='./packages', auther=pam.authenticate)
   bottle.run(app=app, host='0.0.0.0', port=80, server='auto')

   [Ctrl+ D]
   ```

1. Invoke the python-script to start-up **pypiserver**

   ```shell
   python pypiserver-start.py
   ```

> [!NOTE]
> The [python-pam](https://pypi.org/project/python-pam/) module, requires *read* access to **/etc/shadow** file;
> you may add the user under which **pypiserver** runs into the *shadow*
> group, with a command like this: **sudo usermod -a -G shadow pypy-user**.

### Use with MicroPython

The MicroPython interpreter for embedded devices can install packages with the
module **upip.py**. The module uses a specialized json-endpoint to retrieve
package information. This endpoint is supported by **pypiserver**.

It can be tested with the UNIX port of **micropython**

```shell
cd micropython
ports/unix/micropython -m tools.upip install -i http://my-server:8080 -p /tmp/mymodules micropython-foobar
```

Installing packages from the REPL of an embedded device works in this way:

```python
import network
import upip

sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect('<your ESSID>', '<your password>')
upip.index_urls = ["http://my-server:8080"]
upip.install("micropython-foobar")
```

Further information on micropython-packaging can be found here: <https://docs.micropython.org/en/latest/reference/packages.html>

### Custom Health Check Endpoint

**pypiserver** provides a default health endpoint at **/health**. It always returns
**200 Ok** if the service is up. Otherwise, it means that the service is not responsive.

In addition, **pypiserver** allows users to customize the health endpoint.
Alphanumeric characters, hyphens, forward slashes and underscores are allowed
and the endpoint should not overlap with any existing routes.
Valid examples: **/healthz**, **/health/live-1**, **/api_health**, **/action/health**

#### Configure a custom health endpoint by CLI arguments

Run pypiserver with **--health-endpoint** argument:

```shell
pypi-server run --health-endpoint /action/health
```

#### Configure a custom health endpoint by script

```python
import pypiserver
from pypiserver import bottle
app = pypiserver.app(root="./packages", health_endpoint="/action/health")
bottle.run(app=app, host="0.0.0.0", port=8080, server="auto")
```

Try **curl <http://localhost:8080/action/health>**

## Sources

To create a copy of the repository, use

```shell
git clone https://github.com/pypiserver/pypiserver.git
cd pypiserver
```

To receive any later changes, in the above folder use:

```shell
git pull
```

## Known Limitations

> [!IMPORTANT]
> **pypiserver** does not implement the full API as seen on [PyPI](https://pypi.org/).
> It implements just enough to make **easy_install**, **pip install**, and
> **search** work.

The following limitations are known:

- Command **pypi -U** that compares uploaded packages with *pypi* to see if
  they are outdated, does not respect a http-proxy environment variable
  (see [#19](https://github.com/pypiserver/pypiserver/issues/19).
- It accepts documentation uploads but does not save them to
  disk (see [#47](https://github.com/pypiserver/pypiserver/issues/47) for a
  discussion)
- It does not handle misspelled packages as *pypi-repo* does,
  therefore it is suggested to use it with **--extra-index-url** instead
  of **--index-url** (see [#38](https://github.com/pypiserver/pypiserver/issues/38)).

Please use Github's [bugtracker](https://github.com/pypiserver/pypiserver/issues)
for other bugs you find.

## Similar Projects

There are lots of other projects, which allow you to run your own
PyPI server. If **pypiserver** doesn't work for you, the following are
among the most popular alternatives:

- [devpi-server](https://pypi.org/project/devpi/):
  a reliable fast pypi.org caching server, part of
  the comprehensive [github-style pypi index server and packaging meta tool](https://pypi.org/project/devpi/).
  (version: 2.1.4, access date: 8/3/2015)

- Check this SO question: [How to roll my own pypi](http://stackoverflow.com/questions/1235331/how-to-roll-my-own-pypi)

### Unmaintained or archived

These projects were once alternatives to pypiserver but are now either unmaintained or archived.

- [pip2pi](https://github.com/wolever/pip2pi)
  a simple cmd-line tool that builds a PyPI-compatible local folder from pip requirements

- [flask-pypi-proxy](http://flask-pypi-proxy.readthedocs.org/)
  A proxy for PyPI that also enables uploading custom packages.

## Related Software

Though not direct alternatives for **pypiserver**'s use as an index
server, the following is a list of related software projects that you
may want to familiarize with:

- [pypi-uploader](https://pypi.org/project/pypi-uploader/):
  A command-line utility to upload packages to your **pypiserver** from pypi without
  having to store them locally first.

- [twine](https://pypi.org/project/twine/):
  A command-line utility for interacting with PyPI or **pypiserver**.

- [warehouse](https://github.com/pypa/warehouse/):
  the software that powers [PyPI](https://pypi.org/) itself. It is not generally intended to
  be run by end-users.

# Licensing

**pypiserver** contains a copy of [bottle](http://bottlepy.org/) which is
available under the MIT license, and the remaining part is distributed under
the zlib/libpng license. See the **LICENSE.txt** file.
