.. -*- mode: rst; coding: utf-8 -*-

.. image:: pypiserver_logo.png
   :width: 300 px
   :align: center

==============================================================================
pypiserver - minimal PyPI server for use with pip/easy_install
==============================================================================
|pypi-ver| |travis-status| |dependencies| |downloads-count| |python-ver| \
|proj-license|

:Version:     1.2.0
:Date:        2016-06-23
:Source:      https://github.com/pypiserver/pypiserver
:PyPI:        https://pypi.python.org/pypi/pypiserver
:Travis:      https://travis-ci.org/pypiserver/pypiserver
:Maintainer:  Kostis Anagnostopoulos <ankostis@gmail.com>
:License:     zlib/libpng + MIT

*pypiserver* is a minimal PyPI_ compatible server for *pip* or *easy_install*.
It is based on bottle_ and serves packages from regular directories.
Wheels, bdists, eggs and accompanying PGP-signatures can be uploaded
either with *pip*, *setuptools*, *twine* or simply copied with *scp*.


.. contents:: Table of Contents
  :backlinks: top


Quickstart: Installation and Usage
==================================
*pypiserver* ``> 1.2.x`` works with python ``2.7`` and ``3.3+`` or *pypy*.
Python ``3.0 --> 3.2`` may also work, but it is not being tested for these
versions.
For legacy python versions, use ``pypiserver-1.1.x`` series.

Run the following commands to get your *pypiserver* up and running::

  ## Installation.
  pip install pypiserver                ## Or: pypiserver[passlib,watchdog]
  mkdir ~/packages                      ## Copy packages into this directory.

  ## Start server.
  pypi-server -p 8080 ~/packages &      ## Will listen to all IPs.

From the client computer, type this::

  ## Download and Install hosted packages.
  pip install  --extra-index-url http://localhost:8080/simple/ ...
  ## Search hosted packages
  pip search --index http://localhost:8080/simple/ ...

See also `Client-side configurations`_ for avoiding tedious typing.

.. Note::
   The above commands work on a unix-like operating system with a posix shell.
   The ``'~'`` character expands to user's home directory.

   If you're using Windows, you'll have to use their "Windows counterparts".
   The same is true for the rest of this documentation.


Uploading packages from sources, remotely
-----------------------------------------
Instead of copying packages directly to the server's folder,
you may also upload them remotely with a ``python setup.py upload`` command.
Currently only password-protected uploads are supported!

#. First make sure you have the *passlib* module installed (note that
   `passlib>=1.6` is required), which is needed for parsing the Apache
   *htpasswd* file specified by the `-P`, `--passwords` option
   (see next steps)::

     pip install passlib

#. Create the Apache *htpasswd* file with at least one user/password pair
   with this command (you'll be prompted for a password)::

     htpasswd -sc htpasswd.txt <some_username>

   .. Tip:: Read this SO question for running `htpasswd` cmd
      under *Windows*:

         http://serverfault.com/questions/152950/how-to-create-and-edit-htaccess-and-htpasswd-locally-on-my-computer-and-then-u

      or if you have bogus passwords that you don't care because they are for
      an internal service (which is still "bad", from a security prespective...)
      you may use this public service:

         http://www.htaccesstools.com/htpasswd-generator/

     It is also possible to disable authentication even for uploads.
     To avoid lazy security decisions, read help for ``-P`` and ``-a`` options.

#. You  need to restart the server with the `-P` option only once
   (but user/password pairs can later be added or updated on the fly)::

     ./pypi-server -p 8080 -P htpasswd.txt ~/packages &

#. On client-side, edit or create a `~/.pypirc` file with a similar content::

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

#. Then from within the directory of the python-project you wish to upload,
   issue this command::

     python setup.py sdist upload -r local

.. Tip::
   To avoid storing you passwords on disk, in clear text, you may either:

   - use the ``register`` *setuptools*'s command with the ``-r`` option,
     like that::

        python setup.py sdist register -r local upload -r local

   - use `twine`_ library, which
     breaks the procedure in two steps.  In addition, it supports signing
     your files with PGP-Signatures and uploading the generated `.asc` files
     to *pypiserver*::

        twine upload -r local --sign -identity user_name ./foo-1.zip


.. Tip::
    You can also upload packages using `pypi-uploader`_, which
    obviates the need to download packages locally prior to uploading them to
    pypiserver. You can install it with ``pip install pypi-uploader``, and
    assuming you have a ``pypi_local`` source set up in your ``~/.pypirc``,
    use it like this::

        pypiupload packages mock==1.0.1 requests==2.2.1 -i pypi_local
        pypiupload requirements requirements.txt -i pypi_local


Client-side configurations
--------------------------
Always specifying the the pypi url on the command line is a bit
cumbersome. Since *pypiserver* redirects ``pip/easy_install`` to the
``pypi.python.org`` index if it doesn't have a requested package, it's a
good idea to configure them to always use your local pypi index.

Configuring *pip*
~~~~~~~~~~~~~~~~~
For ``pip`` command this can be done by setting the environment variable
``PIP_EXTRA_INDEX_URL`` in your ``.bashr/.profile/.zshrc``::

  export PIP_EXTRA_INDEX_URL=http://localhost:8080/simple/

or by adding the following lines to ``~/.pip/pip.conf``::

  [global]
  extra-index-url = http://localhost:8080/simple/

.. Note::
   If you have installed *pypiserver* on a remote url without *https*
   you wil receive an "untrusted" warning from *pip*, urging you to append
   the ``--trusted-host`` option.  You can also include this option permanently
   in your configuration-files or environment variables.


Configuring *easy_install*
~~~~~~~~~~~~~~~~~~~~~~~~~~
For ``easy_install`` command you may set the following configuration in
``~/.pydistutils.cfg``::

  [easy_install]
  index_url = http://localhost:8080/simple/


Alternative Installation methods
================================
When trying the methods below, first use the following command to check whether
previous versions of *pypiserver* already exist, and (optionally) uninstall them::

  ## VERSION-CHECK: Fails if not installed.
  pypi-server --version

  ## UNINSTALL: Invoke again untill it fails.
  pip uninstall pypiserver


Installing the very latest version
----------------------------------
In case the latest version in *pypi* is a pre-release, you have to use
*pip*'s `--pre` option.  And to update an existing installation combine it
with `--ignore-installed`::

  pip install pypiserver --pre -I

You can even install the latest *pypiserver* directly from *github* with the
following command, assuming you have *git* installed on your `$PATH`::

  pip install git+git://github.com/pypiserver/pypiserver.git


Installing it as standalone script
----------------------------------
The git repository contains a ``pypi-server-standalone.py`` script,
which is a single python file that can be executed without any other
dependencies.

Run the following commands to download the script with ``wget``::

  wget https://raw.github.com/pypiserver/pypiserver/standalone/pypi-server-standalone.py
  chmod +x pypi-server-standalone.py

or with ``curl``::

  curl -O https://raw.github.com/pypiserver/pypiserver/standalone/pypi-server-standalone.py
  chmod +x pypi-server-standalone.py

You can then start-up the server with::

  ./pypi-server-standalone.py

Feel free to rename the script and move it into your ``$PATH``.


Running on *heroku/dotcloud*
----------------------------
https://github.com/dexterous/pypiserver-on-the-cloud contains
instructions on how to run *pypiserver* on one of the supported cloud
service providers.



Detailed Usage
==============
Enter ``pypi-server -h`` in the cmd-line to print a detailed usage message::

  pypi-server [OPTIONS] [PACKAGES_DIRECTORY...]
    start PyPI compatible package server serving packages from
    PACKAGES_DIRECTORY. If PACKAGES_DIRECTORY is not given on the
    command line, it uses the default ~/packages.  pypiserver scans this
    directory recursively for packages. It skips packages and
    directories starting with a dot. Multiple package directories can be
    specified.

  pypi-server understands the following options:

    -p, --port PORT
      listen on port PORT (default: 8080)

    -i, --interface INTERFACE
      listen on interface INTERFACE (default: 0.0.0.0, any interface)

    -a, --authenticate (UPDATE|download|list), ...
      comma-separated list of (case-insensitive) actions to authenticate
      Use '.' or '' for empty. Requires to have set the password (-P option).
      For example to password-protect package downloads (in addition to uploads)
      while leaving listings public, give:
        -P foo/htpasswd.txt  -a update,download
      To drop all authentications, use:
        -P .  -a .
      Note that when uploads are not protected, the `register` command
      is not necessary, but `~/.pypirc` still need username and password fields,
      even if bogus.
      By default, only 'update' is password-protected.

    -P, --passwords PASSWORD_FILE
      use apache htpasswd file PASSWORD_FILE to set usernames & passwords when
      authenticating certain actions (see -a option).
      If you want to allow un-authorized access, set this option and -a
      explicitly to empty (either '.' or'').

    --disable-fallback
      disable redirect to real PyPI index for packages not found in the
      local index

    --fallback-url FALLBACK_URL
      for packages not found in the local index, this URL will be used to
      redirect to (default: http://pypi.python.org/simple)

    --server METHOD
      use METHOD to run the server. Valid values include paste,
      cherrypy, twisted, gunicorn, gevent, wsgiref, auto. The
      default is to use "auto" which chooses one of paste, cherrypy,
      twisted or wsgiref.

    -r, --root PACKAGES_DIRECTORY
      [deprecated] serve packages from PACKAGES_DIRECTORY

    -o, --overwrite
      allow overwriting existing package files

    --hash-algo ALGO
      any `hashlib` available algo used as fragments on package links.
      Set one of (0, no, off, false) to disabled it. (default: md5)

    --welcome HTML_FILE
      uses the ASCII contents of HTML_FILE as welcome message response.

    -v
      enable INFO logging;  repeat for more verbosity.

    --log-conf <FILE>
      read logging configuration from FILE.
      By default, configuration is read from `log.conf` if found in server's dir.

    --log-file <FILE>
      write logging info into this FILE.

    --log-frmt <FILE>
      the logging format-string.  (see `logging.LogRecord` class from standard python library)
      [Default: %(asctime)s|%(name)s|%(levelname)s|%(thread)d|%(message)s]

    --log-req-frmt FORMAT
      a format-string selecting Http-Request properties to log; set to  '%s' to see them all.
      [Default: %(bottle.request)s]

    --log-res-frmt FORMAT
      a format-string selecting Http-Response properties to log; set to  '%s' to see them all.
      [Default: %(status)s]

    --log-err-frmt FORMAT
      a format-string selecting Http-Error properties to log; set to  '%s' to see them all.
      [Default: %(body)s: %(exception)s \n%(traceback)s]

  pypi-server -h
  pypi-server --help
    show this help message

  pypi-server --version
    show pypi-server's version

  pypi-server -U [OPTIONS] [PACKAGES_DIRECTORY...]
    update packages in PACKAGES_DIRECTORY. This command searches
    pypi.python.org for updates and shows a pip command line which
    updates the package.

  The following additional options can be specified with -U:

    -x
      execute the pip commands instead of only showing them

    -d DOWNLOAD_DIRECTORY
      download package updates to this directory. The default is to use
      the directory which contains the latest version of the package to
      be updated.

    -u
      allow updating to unstable version (alpha, beta, rc, dev versions)

  Visit https://github.com/pypiserver/pypiserver for more information.



Managing the package directory
------------------------------
The ``pypi-server`` command has the ``-U`` option that searches for updates of
available packages. It scans the package directory for available
packages and searches on pypi.python.org for updates. Without further
options ``pypi-server -U`` will just print a list of commands which must
be run in order to get the latest version of each package. Output
looks like::

    $ ./pypi-server -U
    checking 106 packages for newer version

    .........u.e...........e..u.............
    .....e..............................e...
    ..........................

    no releases found on pypi for PyXML, Pymacs, mercurial, setuptools

    # update raven from 1.4.3 to 1.4.4
    pip -q install --no-deps  --extra-index-url http://pypi.python.org/simple -d /home/ralf/packages/mirror raven==1.4.4

    # update greenlet from 0.3.3 to 0.3.4
    pip -q install --no-deps  --extra-index-url http://pypi.python.org/simple -d /home/ralf/packages/mirror greenlet==0.3.4

It first prints for each package a single character after checking the
available versions on pypi. A dot(`.`) means the package is up-to-date, ``'u'``
means the package can be updated and ``'e'`` means the list of releases on
pypi is empty. After that it shows a *pip* command line which can be used
to update a one package. Either copy and paste that or run
``pypi-server -Ux`` in order to really execute those commands. You need
to have *pip* installed for that to work however.

Specifying an additional ``-u`` option will also allow alpha, beta and
release candidates to be downloaded. Without this option these
releases won't be considered.


Serving thousands of packages
-----------------------------

By default, *pypiserver* scans the entire packages directory each time an
incoming HTTP request occurs. This isn't a problem for a small number of
packages, but causes noticeable slowdowns when serving thousands or tens
of thousands of packages.

If you run into this problem, significant speedups can be gained by enabling
pypiserver's directory caching functionality. The only requirement is to
install the ``watchdog`` package, or it can be installed by installing
``pypiserver`` using the ``cache`` extras option::

    pip install pypiserver[cache]

If you are using a static webserver such as *Apache* or *nginx* as
a reverse-proxy for pypiserver, additional speedup can be gained by
directly serving the packages directory:

For instance, in *nginx* you may adding the following config to serve
packages-directly directly (take care not to expose "sensitive" files)::

    location /packages/ {
      root /path/to/packages/parentdir;
    }

If you have packages that are very large, you may find it helpful to
disable hashing of files (set ``--hash-algo=off``, or ``hash_algo=None`` when
using wsgi).


Managing Automated Startup
--------------------------
There are a variety of options for handling the automated starting of
pypiserver upon system startup. Two of the most common are *systemd* and
*supervisor*.


Running as a *systemd* service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
*systemd* is installed by default on most modern Linux systems and as such,
it is an excellent option for managing the pypiserver process. An example
config file for ``systemd`` can be seen below::

    [Unit]
    Description=A minimal PyPI server for use with pip/easy_install.
    After=network.target

    [Service]
    Type=simple
    # systemd requires absolute path here too.
    PIDFile=/var/run/pypiserver.pid
    User=www-data
    Group=www-data

    ExecStart=/usr/local/bin/pypi-server -p 8080 -a update,download --log-file /var/log/pypiserver.log --P /etc/nginx/.htpasswd /var/www/pypi
    ExecStop=/bin/kill -TERM $MAINPID
    ExecReload=/bin/kill -HUP $MAINPID
    Restart=always

    WorkingDirectory=/var/www/pypi

    TimeoutStartSec=3
    RestartSec=5

    [Install]
    WantedBy=multi-user.target

Adjusting the paths and adding this file as ``pypiserver.service`` into your
``systemd/system`` directory will allow management of the pypiserver process with
``systemctl``, e.g. ``systemctl start pypiserver``.

More useful information about *systemd* can be found at
https://www.digitalocean.com/community/tutorials/how-to-use-systemctl-to-manage-systemd-services-and-units


Launching through *supervisor*
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`supervisor <http://supervisord.org/>`_ has the benefit of being a pure python
package and as such, it provides excellent cross-platform support for process
management. An example configuration file for ``supervisor`` is given below::

    [program:pypi]
    command=/home/pypi/pypi-venv/bin/pypi-server -p 7001 -P /home/pypi/.htaccess /home/pypi/packages
    directory=/home/pypi
    user=pypi
    autostart=true
    autorestart=true
    stderr_logfile=/var/log/pypiserver.err.log
    stdout_logfile=/var/log/pypiserver.out.log

From there, the process can be managed via ``supervisord`` using ``supervisorctl``.


Using a different WSGI server
-----------------------------
- *pypiserver* ships with it's own copy of bottle.
  It's possible to use bottle with different WSGI servers.

- *pypiserver* chooses any of the
  following *paste*, *cherrypy*, *twisted*, *wsgiref* (part of python) if
  available.

- If none of the above servers matches your needs, pypiserver also
  exposes an API to get the internal WSGI app, which you can then run
  under any WSGI server you like. ``pypiserver.app`` has the following
  interface::

    def app(root=None,
        redirect_to_fallback=True,
        fallback_url="http://pypi.python.org/simple")

  and returns the WSGI application. `root` is the package directory,
  `redirect_to_fallback` specifies whether to redirect to `fallback_url` when
  a package is missing.


gunicorn
~~~~~~~~

The following command uses *gunicorn* to start *pypiserver*::

  gunicorn -w4 'pypiserver:app(root="/home/ralf/packages")'

or when using multiple roots::

  gunicorn -w4 'pypiserver:app(root=["/home/ralf/packages", "/home/ralf/experimental"])'


apache/mod_wsgi
~~~~~~~~~~~~~~~
In case you're using *apache2* with *mod_wsgi*, the following config-file
(contributed by Thomas Waldmann) can be used::

  # An example pypiserver.wsgi for use with apache2 and mod_wsgi, edit as necessary.
  #
  # apache virtualhost configuration for mod_wsgi daemon mode:
  #    Alias /robots.txt /srv/yoursite/htdocs/robots.txt
  #    WSGIPassAuthorization On
  #    WSGIScriptAlias /     /srv/yoursite/cfg/pypiserver.wsgi
  #    WSGIDaemonProcess     pypisrv user=pypisrv group=pypisrv processes=1 threads=5 maximum-requests=500 umask=0007 display-name=wsgi-pypisrv inactivity-timeout=300
  #    WSGIProcessGroup      pypisrv

  PACKAGES = "/srv/yoursite/packages"
  HTPASSWD = "/srv/yoursite/htpasswd"
  import pypiserver
  application = pypiserver.app(root=PACKAGES, redirect_to_fallback=True, password_file=HTPASSWD)


paste/pastedeploy
~~~~~~~~~~~~~~~~~
`paste <http://pythonpaste.org/>`_ allows to run multiple WSGI applications
under different URL paths. Therefore it's possible to serve different set
of packages on different paths.

The following example ``paste.ini`` could be used to serve stable and
unstable packages on different paths::

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

.. Note::
   You need to install some more dependencies for this to work, like::

        pip install paste pastedeploy gunicorn pypiserver

   The server can then start with::

        gunicorn_paster paste.ini



Sources
=======
To create a copy of the repository, use::

    git clone https://github.com/pypiserver/pypiserver.git
    cd pypiserver

To receive any later changes, in the above folder use::

    git pull


Known Limitations
=================
*pypiserver* does not implement the full API as seen on PyPI_. It
implements just enough to make ``easy_install`` and ``pip install`` to work.

The following limitations are known:

- Command ``pypi -U`` that compares uploaded packages with *pypi* to see if
  they are outdated, does not respect a http-proxy environment variable
  (see https://github.com/pypiserver/pypiserver/issues/19).
- It accepts documentation uploads but does not save them to
  disk (see https://github.com/pypiserver/pypiserver/issues/47 for a
  discussion)
- It does not handle misspelled packages as *pypi-repo* does,
  therefore it is suggested to use it with ``--extra-index-url`` instead
  of ``--index-url`` (see https://github.com/pypiserver/pypiserver/issues/38).

Please use Github's `bugtracker <https://github.com/pypiserver/pypiserver/issues>`_
for other bugs you find.



Similar Projects
================
There are lots of other projects, which allow you to run your own
PyPI server. If *pypiserver* doesn't work for you, the following are
among the most popular alternatives:

- `devpi-server <https://pypi.python.org/pypi/devpi-server>`_:
  a reliable fast pypi.python.org caching server, part of
  the comprehensive `github-style pypi index server and packaging meta tool
  <https://pypi.python.org/pypi/devpi>`_.
  (version: 2.1.4, access date: 8/3/2015)

- `pip2pi <https://github.com/wolever/pip2pi>`_
  a simple cmd-line tool that builds a PyPI-compatible local folder from pip requirements
  (version: 0.6.7, access date: 8/3/2015)

- `flask-pypi-proxy <http://flask-pypi-proxy.readthedocs.org/>`_
  A proxy for PyPI that also enables also uploading custom packages.

- `twine`_:
  A command-line utility for interacting with PyPI or *pypiserver*.

- `pypi-uploader`_:
  A command-line utility to upload packages to your *pypiserver* from pypi without
  having to store them locally first.

- Check this SO question: ` How to roll my own pypi
  <http://stackoverflow.com/questions/1235331/how-to-roll-my-own-pypi>`_



License
=======
*pypiserver* contains a copy of bottle_ which is available under the
*MIT* license, and the remaining part is distributed under the *zlib/libpng* license.
See the ``LICENSE.txt`` file.



.. _bottle: http://bottlepy.org
.. _PyPI: http://pypi.python.org
.. _twine: https://pypi.python.org/pypi/twine
.. _pypi-uploader: https://pypi.python.org/pypi/pypi-uploader
.. |travis-status| image:: https://travis-ci.org/pypiserver/pypiserver.svg
    :alt: Travis build status
    :scale: 100%
    :target: https://travis-ci.org/pypiserver/pypiserver

.. |pypi-ver| image::  https://img.shields.io/pypi/v/pypiserver.svg
    :target: https://pypi.python.org/pypi/pypiserver/
    :alt: Latest Version in PyPI

.. |python-ver| image:: https://img.shields.io/pypi/pyversions/pypiserver.svg
    :target: https://pypi.python.org/pypi/pypiserver/
    :alt: Supported Python versions

.. |downloads-count| image:: https://img.shields.io/pypi/dm/pypiserver.svg?period=week
    :target: https://pypi.python.org/pypi/pypiserver/
    :alt: Downloads

.. |proj-license| image:: https://img.shields.io/badge/license-BSD%2Bzlib%2Flibpng-blue.svg
    :target: https://raw.githubusercontent.com/pypiserver/pypiserver/master/LICENSE.txt
    :alt: Project License

.. |dependencies| image:: https://img.shields.io/requires/github/pypiserver/pypiserver.svg
    :alt: Dependencies up-to-date?
