.. -*- mode: rst; coding: utf-8 -*-

.. image:: pypiserver_logo.png
   :width: 300 px
   :align: center

==============================================================================
pypiserver - minimal PyPI server for use with pip/easy_install
==============================================================================
|pypi-ver| |travis-status| |dependencies| |python-ver| |proj-license|

:Version:     1.4.2
:Date:        2020-10-10
:Source:      https://github.com/pypiserver/pypiserver
:PyPI:        https://pypi.org/project/pypiserver/
:Travis:      https://travis-ci.org/pypiserver/pypiserver
:Maintainers: Kostis Anagnostopoulos <ankostis@gmail.com>,
              Matthew Planchard <mplanchard@gmail.com>
:License:     zlib/libpng + MIT
:Community:   https://pypiserver.zulipchat.com

Chat with us on `Zulip <https://pypiserver.zulipchat.com>`_!

``pypiserver`` is a minimal PyPI_ compatible server for ``pip`` or ``easy_install``.
It is based on bottle_ and serves packages from regular directories.
Wheels, bdists, eggs and accompanying PGP-signatures can be uploaded
either with ``pip``, ``setuptools``, ``twine``, ``pypi-uploader``, or simply copied
with ``scp``.

.. note::
   The official software powering PyPI_ is Warehouse_. However, Warehouse_
   is fairly specialized to be ``pypi.org``'s own software, and should not
   be used in other contexts. In particular, it does not officially support
   being used as a custom package index by users wishing to serve their own
   packages.

   ``pypiserver`` implements the same interfaces as `PyPI`_, allowing
   standard Python packaging tooling such as ``pip`` and ``twine`` to
   interact with it as a package index just as they would with PyPI_, while
   making it much easier to get a running index server.

.. contents:: Table of Contents
  :backlinks: top


Quickstart: Installation and Usage
==================================

``pypiserver`` > 1.2.x works with Python 2.7 and 3.5+ or PyPy.
Older Python versions may still work, but they are not tested.
For legacy Python versions, use ``pypiserver-1.1.x`` series.

.. Tip::
   The commands below work on a unix-like operating system with a posix shell.
   The ``'~'`` character expands to user's home directory.

   If you're using Windows, you'll have to use their "Windows counterparts".
   The same is true for the rest of this documentation.

1. Install ``pypiserver`` with this command::

    pip install pypiserver                # Or: pypiserver[passlib,watchdog]
    mkdir ~/packages                      # Copy packages into this directory.

   See also `Alternative Installation methods`_.

2. Copy some packages into your ``~/packages`` folder and then
   get your ``pypiserver`` up and running::

    pypi-server -p 8080 ~/packages &      # Will listen to all IPs.

3. From the client computer, type this::

    # Download and install hosted packages.
    pip install --extra-index-url http://localhost:8080/simple/ ...

    # or
    pip install --extra-index-url http://localhost:8080 ...

    # Search hosted packages.
    pip search --index http://localhost:8080 ...

    # Note that pip search does not currently work with the /simple/ endpoint.

   See also `Client-side configurations`_ for avoiding tedious typing.

4. Enter ``pypi-server -h`` in the cmd-line to print a detailed usage message::

    pypi-server [OPTIONS] [PACKAGES_DIRECTORY...]
      start PyPI compatible package server serving packages from
      PACKAGES_DIRECTORY. If PACKAGES_DIRECTORY is not given on the
      command line, it uses the default ~/packages. pypiserver scans this
      directory recursively for packages. It skips packages and
      directories starting with a dot. Multiple package directories can be
      specified.

    pypi-server understands the following options:

      -p, --port PORT
        Listen on port PORT (default: 8080).

      -i, --interface INTERFACE
        Listen on interface INTERFACE (default: 0.0.0.0, any interface).

      -a, --authenticate (update|download|list), ...
        Comma-separated list of (case-insensitive) actions to authenticate.
        Requires to have set the password (-P option).
        To password-protect package downloads (in addition to uploads) while
        leaving listings public, use:
          -P foo/htpasswd.txt -a update,download
        To allow unauthorized access, use:
          -P . -a .
        Note that when uploads are not protected, the `register` command
        is not necessary, but `~/.pypirc` still need username and password fields,
        even if bogus.
        By default, only 'update' is password-protected.

      -P, --passwords PASSWORD_FILE
        Use apache htpasswd file PASSWORD_FILE to set usernames & passwords when
        authenticating certain actions (see -a option).
        To allow unauthorized access, use:
          -P . -a .

      --disable-fallback
        Disable redirect to real PyPI index for packages not found in the
        local index.

      --fallback-url FALLBACK_URL
        For packages not found in the local index, this URL will be used to
        redirect to (default: https://pypi.org/simple/).

      --server METHOD
        Use METHOD to run the server. Valid values include paste,
        cherrypy, twisted, gunicorn, gevent, wsgiref, auto. The
        default is to use "auto" which chooses one of paste, cherrypy,
        twisted or wsgiref.

      -r, --root PACKAGES_DIRECTORY
        [deprecated] Serve packages from PACKAGES_DIRECTORY.

      -o, --overwrite
        Allow overwriting existing package files.

      --hash-algo ALGO
        Any `hashlib` available algo used as fragments on package links.
        Set one of (0, no, off, false) to disabled it (default: md5).

      --welcome HTML_FILE
        Uses the ASCII contents of HTML_FILE as welcome message response.

      -v
        Enable verbose logging; repeat for more verbosity.

      --log-conf <FILE>
        Read logging configuration from FILE.
        By default, configuration is read from `log.conf` if found in server's dir.

      --log-file <FILE>
        Write logging info into this FILE.

      --log-frmt <FILE>
        The logging format-string (see `logging.LogRecord` class from standard python library).
        [Default: %(asctime)s|%(name)s|%(levelname)s|%(thread)d|%(message)s]

      --log-req-frmt FORMAT
        A format-string selecting Http-Request properties to log; set to '%s' to see them all.
        [Default: %(bottle.request)s]

      --log-res-frmt FORMAT
        A format-string selecting Http-Response properties to log; set to  '%s' to see them all.
        [Default: %(status)s]

      --log-err-frmt FORMAT
        A format-string selecting Http-Error properties to log; set to  '%s' to see them all.
        [Default: %(body)s: %(exception)s \n%(traceback)s]

      --cache-control AGE
        Add "Cache-Control: max-age=AGE, public" header to package downloads.
        Pip 6+ needs this for caching.

    pypi-server -h, --help
      Show this help message.

    pypi-server --version
      Show pypi-server's version.

    pypi-server -U [OPTIONS] [PACKAGES_DIRECTORY...]
      Update packages in PACKAGES_DIRECTORY. This command searches
      pypi.org for updates and shows a pip command line which
      updates the package.

    The following additional options can be specified with -U:

      -x
        Execute the pip commands instead of only showing them.

      -d DOWNLOAD_DIRECTORY
        Download package updates to this directory. The default is to use
        the directory which contains the latest version of the package to
        be updated.

      -u
        Allow updating to unstable version (alpha, beta, rc, dev versions).

    Visit https://github.com/pypiserver/pypiserver for more information.


Client-Side Configurations
==========================

Always specifying the the pypi url on the command line is a bit
cumbersome. Since ``pypiserver`` redirects ``pip/easy_install`` to the
``pypi.org`` index if it doesn't have a requested package, it is a
good idea to configure them to always use your local pypi index.

Configuring ``pip``
-------------------

For ``pip`` command this can be done by setting the environment variable
``PIP_EXTRA_INDEX_URL`` in your ``.bashr/.profile/.zshrc``::

  export PIP_EXTRA_INDEX_URL=http://localhost:8080/simple/

or by adding the following lines to ``~/.pip/pip.conf``::

  [global]
  extra-index-url = http://localhost:8080/simple/

.. Note::
   If you have installed ``pypiserver`` on a remote url without *https*
   you wil receive an "untrusted" warning from *pip*, urging you to append
   the ``--trusted-host`` option.  You can also include this option permanently
   in your configuration-files or environment variables.

Configuring ``easy_install``
----------------------------

For ``easy_install`` command you may set the following configuration in
``~/.pydistutils.cfg``::

  [easy_install]
  index_url = http://localhost:8080/simple/


Uploading Packages Remotely
===========================

Instead of copying packages directly to the server's folder (i.e. with ``scp``),
you may use python tools for the task, e.g. ``python setup.py upload``.
In that case, ``pypiserver`` is responsible for authenticating the upload-requests.

.. Note::
  We strongly advise to password-protected your uploads!

  It is possible to disable authentication for uploads (e.g. in intranets).
  To avoid lazy security decisions, read help for ``-P`` and ``-a`` options.

*Apache*-Like Authentication (``htpasswd``)
-------------------------------------------

#. First make sure you have the *passlib* module installed (note that
   ``passlib>=1.6`` is required), which is needed for parsing the Apache
   *htpasswd* file specified by the ``-P``, ``--passwords`` option
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

   .. Tip:: When accessing pypiserver via the api, alternate authentication
      methods are available via the ``auther`` config flag. Any callable
      returning a boolean can be passed through to the pypiserver config in
      order to provide custom authentication. For example, to configure
      pypiserver to authenticate using the `python-pam`_::

        import pam
        pypiserver.default_config(auther=pam.authenticate)

      Please see `Using Ad-hoc authentication providers`_ for more information.

#. You  need to restart the server with the ``-P`` option only once
   (but user/password pairs can later be added or updated on the fly)::

     ./pypi-server -p 8080 -P htpasswd.txt ~/packages &

Upload with ``setuptools``
--------------------------

#. On client-side, edit or create a ``~/.pypirc`` file with a similar content::

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

Upload with ``twine``
---------------------

To avoid storing you passwords on disk, in clear text, you may either:

- use the ``register`` *setuptools*'s command with the ``-r`` option,
  like that::

     python setup.py sdist register -r local upload -r local

- use `twine`_ library, which
  breaks the procedure in two steps.  In addition, it supports signing
  your files with PGP-Signatures and uploading the generated `.asc` files
  to ``pypiserver``::

     twine upload -r local --sign -identity user_name ./foo-1.zip


Using the Docker Image
======================

Starting with version 1.2.5, official Docker images will be built for each
push to master, each dev, alpha, or beta release, and each final release.
The most recent full release will always be available under the tag ``latest``,
and the current master branch will always be available under the tag
``unstable``.

You can always check to see what tags are currently available at our
`Docker Repo`_.

To run the most recent release of ``pypiserver`` with Docker, simply::

    docker run pypiserver/pypiserver:latest

This starts ``pypiserver`` serving packages from the ``/data/packages``
directory inside the container, listening on the container port 8080.

The container takes all the same arguments as the normal ``pypi-server``
executable, with the exception of the internal container port (``-p``),
which will always be 8080.

Of course, just running a container isn't that interesting. To map
port 80 on the host to port 8080 on the container::

    docker run -p 80:8080 pypiserver/pypiserver:latest

You can now access your ``pypiserver`` at ``localhost:80`` in a web browser.

To serve packages from a directory on the host, e.g. ``~/packages``::

    docker run -p 80:8080 -v ~/packages:/data/packages pypiserver/pypiserver:latest

To authenticate against a local ``.htpasswd`` file::

    docker run -p 80:8080 -v ~/.htpasswd:/data/.htpasswd pypiserver/pypiserver:latest -P .htpasswd packages

You can also specify ``pypiserver`` to run as a Docker service using a
composefile. An example composefile is `provided <docker-compose.yml>`_.


.. _`docker repo`: https://hub.docker.com/r/pypiserver/pypiserver/tags/


Alternative Installation Methods
================================

When trying the methods below, first use the following command to check whether
previous versions of ``pypiserver`` already exist, and (optionally) uninstall them::

  # VERSION-CHECK: Fails if not installed.
  pypi-server --version

  # UNINSTALL: Invoke again untill it fails.
  pip uninstall pypiserver

Installing the Very Latest Version
----------------------------------

In case the latest version in *pypi* is a pre-release, you have to use
*pip*'s `--pre` option.  And to update an existing installation combine it
with `--ignore-installed`::

  pip install pypiserver --pre -I

You can even install the latest ``pypiserver`` directly from *github* with the
following command, assuming you have *git* installed on your ``PATH``::

  pip install git+git://github.com/pypiserver/pypiserver.git

Installing It As Standalone Script
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

Running on Heroku/Dotcloud
--------------------------

https://github.com/dexterous/pypiserver-on-the-cloud contains
instructions on how to run ``pypiserver`` on one of the supported cloud
service providers.


Recipes
=======

Managing the Package Directory
------------------------------

The ``pypi-server`` command has the ``-U`` option that searches for updates of
available packages. It scans the package directory for available
packages and searches on pypi.org for updates. Without further
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
    pip -q install --no-deps  --extra-index-url https://pypi.org/simple/ -d /home/ralf/packages/mirror raven==1.4.4

    # update greenlet from 0.3.3 to 0.3.4
    pip -q install --no-deps  --extra-index-url https://pypi.org/simple/ -d /home/ralf/packages/mirror greenlet==0.3.4

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

Serving Thousands of Packages
-----------------------------

By default, ``pypiserver`` scans the entire packages directory each time an
incoming HTTP request occurs. This isn't a problem for a small number of
packages, but causes noticeable slow-downs when serving thousands of packages.

If you run into this problem, significant speedups can be gained by enabling
pypiserver's directory caching functionality. The only requirement is to
install the ``watchdog`` package, or it can be installed during ``pypiserver``
installation, by specifying the ``cache`` extras option::

    pip install pypiserver[cache]

Additional speedups can be obtained by using your webserver's builtin
caching functionality. For example, if you are using `nginx` as a
reverse-proxy as described below in `Behind a reverse proxy`_, you can
easily enable caching. For example, to allow nginx to cache up to
10 gigabytes of data for up to 1 hour::

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

Using webserver caching is especially helpful if you have high request
volume. Using `nginx` caching, a real-world pypiserver installation was
able to easily support over 1000 package downloads/min at peak load.

Managing Automated Startup
--------------------------

There are a variety of options for handling the automated starting of
pypiserver upon system startup. Two of the most common are *systemd* and
*supervisor* for linux systems. For windows creating services with scripts isn't
an easy task without a third party tool such as *NSSM*.

Running As a ``systemd`` Service
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``systemd`` is installed by default on most modern Linux systems and as such,
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

    ExecStart=/usr/local/bin/pypi-server -p 8080 -a update,download --log-file /var/log/pypiserver.log -P /etc/nginx/.htpasswd /var/www/pypi
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

Launching through ``supervisor``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`supervisor <http://supervisord.org/>`_ has the benefit of being a pure python
package and as such, it provides excellent cross-platform support for process
management. An example configuration file for ``supervisor`` is given below::

    [program:pypi]
    command=/home/pypi/pypi-venv/bin/pypi-server -p 7001 -P /home/pypi/.htpasswd /home/pypi/packages
    directory=/home/pypi
    user=pypi
    autostart=true
    autorestart=true
    stderr_logfile=/var/log/pypiserver.err.log
    stdout_logfile=/var/log/pypiserver.out.log

From there, the process can be managed via ``supervisord`` using ``supervisorctl``.

Running As a service with ``NSSM`` (Windows)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download NSSM from https://nssm.cc unzip to a desired location such as Program Files. Decide whether you are going
to use win32 or win64, and add that exe to environment PATH.

Create a start_pypiserver.bat::

    pypi-server -p 8080 C:\Path\To\Packages &

Test the batch file by running it first before creating the service. Make sure you can access
the server remotely, and install packages. If you can, proceed, if not troubleshoot until you can.
This will ensure you know the server works, before adding NSSM into the mix.

From the command prompt::

    nssm install pypiserver

This command will launch a NSSM gui application::

    Path: C:\Path\To\start_pypiserver.bat
    Startup directory: Auto generates when selecting path
    Service name: pypiserver

There are more tabs, but that is the basic setup. If the service needs to be running with a certain
login credentials, make sure you enter those credentials in the logon tab.

Start the service::

    nssm start pypiserver

Other useful commands::

    nssm --help
    nssm stop <servicename>
    nssm restart <servicename>
    nssm status <servicename>

For detailed information please visit https://nssm.cc

Using a Different WSGI Server
-----------------------------

- The ``bottle`` web-server which supports many WSGI-servers, among others,
  ``paste``, ``cherrypy``, ``twisted`` and ``wsgiref`` (part of Python); you select
  them using the ``--server`` flag.

- You may view all supported WSGI servers using the following interactive code::

    >>> from pypiserver import bottle
    >>> list(bottle.server_names.keys())
    ['cgi', 'gunicorn', 'cherrypy', 'eventlet', 'tornado', 'geventSocketIO',
    'rocket', 'diesel', 'twisted', 'wsgiref', 'fapws3', 'bjoern', 'gevent',
    'meinheld', 'auto', 'aiohttp', 'flup', 'gae', 'paste', 'waitress']

- If none of the above servers matches your needs, invoke just the
  ``pypiserver:app()`` method which returns the internal WSGI-app WITHOUT
  starting-up a server - you may then send it to any WSGI server you like.
  Read also the `Utilizing the API`_ section.

- Some examples are given below - you may find more details in `bottle
  site <http://bottlepy.org/docs/dev/deployment.html#switching-the-server-backend>`_.

Apache (``mod_wsgi``)
~~~~~~~~~~~~~~~~~~~~~

To use your *Apache2* with ``pypiserver``, prefer to utilize ``mod_wsgi`` as
explained in `bottle's documentation <http://bottlepy.org/docs/dev/deployment.html#apache-mod-wsgi>`_.

.. Note::
   If you choose instead to go with ``mod_proxy``, mind that you may bump into problems
   with the prefix-path (see `#155 <https://github.com/pypiserver/pypiserver/issues/155>`_).

1. Adapt and place the following *Apache* configuration either into top-level scope,
   or inside some ``<VirtualHost>`` (contributed by Thomas Waldmann)::

        WSGIScriptAlias   /     /yoursite/wsgi/pypiserver-wsgi.py
        WSGIDaemonProcess       pypisrv user=pypisrv group=pypisrv umask=0007 \
                                processes=1 threads=5 maximum-requests=500 \
                                display-name=wsgi-pypisrv inactivity-timeout=300
        WSGIProcessGroup        pypisrv
        WSGIPassAuthorization On    # Required for authentication (https://github.com/pypiserver/pypiserver/issues/288)

        <Directory /yoursite/wsgi >
            Require all granted
        </Directory>

   or if using older ``Apache < 2.4``, substitute the last part with this::

        <Directory /yoursite/wsgi >
            Order deny,allow
            Allow from all
        </Directory>

2. Then create the ``/yoursite/cfg/pypiserver.wsgi`` file and make sure that
   the ``user`` and ``group`` of the ``WSGIDaemonProcess`` directive
   (``pypisrv:pypisrv`` in the example) have the read permission on it::

        import pypiserver

        conf = pypiserver.default_config(
            root =          "/yoursite/packages",
            password_file = "/yoursite/htpasswd", )
        application = pypiserver.app(**conf)


   .. Tip::
      If you have installed ``pypiserver`` in a virtualenv, follow ``mod_wsgi``'s
      `instructions <http://modwsgi.readthedocs.io/en/develop/user-guides/virtual-environments.html>`_
      and prepend the python code above with the following::

            import site

            site.addsitedir('/yoursite/venv/lib/pythonX.X/site-packages')

.. Note::
   For security reasons, notice that the ``Directory`` directive grants access
   to a directory holding the ``wsgi`` start-up script, alone; nothing else.

.. Note::
   To enable HTTPS support on Apache, configure the directive that contains the
   WSGI configuration to use SSL.

``gunicorn``
~~~~~~~~~~~~

The following command uses ``gunicorn`` to start ``pypiserver``::

  gunicorn -w4 'pypiserver:app(root="/home/ralf/packages")'

or when using multiple roots::

  gunicorn -w4 'pypiserver:app(root=["/home/ralf/packages", "/home/ralf/experimental"])'

``paste``
~~~~~~~~~

`paste <http://pythonpaste.org/>`_ allows to run multiple WSGI applications
under different URL paths. Therefore it is possible to serve different set
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


Behind a Reverse Proxy
----------------------

You can run ``pypiserver`` behind a reverse proxy as well.

Nginx
~~~~~

Extend your nginx configuration::

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

As of pypiserver 1.3, you may also use the `X-Forwarded-Host` header in your
reverse proxy config to enable changing the base URL. For example if you
want to host pypiserver under a particular path on your server::

    upstream pypi {
      server              locahost:8000;
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

Supporting HTTPS
~~~~~~~~~~~~~~~~

Using a reverse proxy is the preferred way of getting pypiserver behind
HTTPS. For example, to put pypiserver behind HTTPS on port 443, with
automatic HTTP redirection, using `nginx`::

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

Please see `nginx's HTTPS docs for more details <http://nginx.org/en/docs/http/configuring_https_servers.html>`_.

Getting and keeping your certificates up-to-date can be simplified using,
for example, using `certbot and letsencrypt <https://www.digitalocean.com/community/tutorials/how-to-secure-nginx-with-let-s-encrypt-on-ubuntu-18-04>`_.

Traefik
~~~~~~~

It is also possible to use `Traefik <https://docs.traefik.io/>`_ to put pypiserver behind HTTPS on port 443, with
automatic HTTP redirection using Docker Compose. Please see the provided `<docker-compose.yml>`_ example for more information.

Utilizing the API
-----------------

In order to enable ad-hoc authentication-providers or to use WSGI-servers
not supported by *bottle* out-of-the-box, you needed to launch ``pypiserver``
via its API.

- The main entry-point for configuring ``pypiserver`` is the `pypiserver:app()
  <https://github.com/pypiserver/pypiserver/blob/master/pypiserver/__init__.py#L116>`_
  function.  This function returns the internal WSGI-app that you my then
  send to any WSGI-server you like.

- To get all ``pypiserver:app()`` keywords and their explanations, read the
  function `pypiserver:default_config()
  <https://github.com/pypiserver/pypiserver/blob/master/pypiserver/__init__.py#L35>`_.

- Finally, to fire-up a WSGI-server with the configured app, invoke
  the ``bottle:run(app, host, port, server)`` function.
  Note that ``pypiserver`` ships with it is own copy of *bottle*; to use it,
  import it like that: ``from pypiserver import bottle``

Using Ad-Hoc Authentication Providers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``auther`` keyword of ``pypiserver:app()`` function maybe set only using
the API. This can be any callable that returns a boolean when passed
the *username* and the *password* for a given request.

For example, to authenticate users based on the ``/etc/passwd`` file under Unix,
you may delegate such decisions to the `python-pam`_ library by following
these steps:

1. Ensure ``python-pam`` module is installed::

    pip install python-pam

2. Create a python-script along these lines::

    $ cat > pypiserver-start.py
    import pypiserver
    from pypiserver import bottle
    import pam
    app = pypiserver.app(root='./packages', auther=pam.authenticate)
    bottle.run(app=app, host='0.0.0.0', port=80, server='auto')

    [Ctrl+ D]

3. Invoke the python-script to start-up ``pypiserver``::

    $ python pypiserver-start.py


.. Note::
   The `python-pam`_ module, requires *read* access to ``/etc/shadow`` file;
   you may add the user under which ``pypiserver`` runs into the *shadow*
   group, with a command like this: ``sudo usermod -a -G shadow pypy-user``.


Sources
=======

To create a copy of the repository, use::

    git clone https://github.com/pypiserver/pypiserver.git
    cd pypiserver

To receive any later changes, in the above folder use::

    git pull


Known Limitations
=================

``pypiserver`` does not implement the full API as seen on PyPI_. It
implements just enough to make ``easy_install``, ``pip install``, and
``search`` work.

The following limitations are known:

- Command ``pypi -U`` that compares uploaded packages with *pypi* to see if
  they are outdated, does not respect a http-proxy environment variable
  (see `#19 <https://github.com/pypiserver/pypiserver/issues/19>`_).
- It accepts documentation uploads but does not save them to
  disk (see `#47 <https://github.com/pypiserver/pypiserver/issues/47>`_ for a
  discussion)
- It does not handle misspelled packages as *pypi-repo* does,
  therefore it is suggested to use it with ``--extra-index-url`` instead
  of ``--index-url`` (see `#38 <https://github.com/pypiserver/pypiserver/issues/38>`_).

Please use Github's `bugtracker <https://github.com/pypiserver/pypiserver/issues>`_
for other bugs you find.


Similar Projects
================

There are lots of other projects, which allow you to run your own
PyPI server. If ``pypiserver`` doesn't work for you, the following are
among the most popular alternatives:

- `devpi-server <https://pypi.org/project/devpi/>`_:
  a reliable fast pypi.org caching server, part of
  the comprehensive `github-style pypi index server and packaging meta tool
  <https://pypi.org/project/devpi/>`_.
  (version: 2.1.4, access date: 8/3/2015)

- Check this SO question: `How to roll my own pypi
  <http://stackoverflow.com/questions/1235331/how-to-roll-my-own-pypi>`_


Unmaintained or archived
------------------------

These projects were once alternatives to pypiserver but are now either unmaintained or archived.

- `pip2pi <https://github.com/wolever/pip2pi>`_
  a simple cmd-line tool that builds a PyPI-compatible local folder from pip requirements

- `flask-pypi-proxy <http://flask-pypi-proxy.readthedocs.org/>`_
  A proxy for PyPI that also enables also uploading custom packages.


Related Software
================

Though not direct alternatives for ``pypiserver``'s use as an index
server, the following is a list of related software projects that you
may want to familiarize with:

- `pypi-uploader`_:
  A command-line utility to upload packages to your ``pypiserver`` from pypi without
  having to store them locally first.

- `twine`_:
  A command-line utility for interacting with PyPI or ``pypiserver``.

- `warehouse`_:
  the software that powers PyPI_ itself. It is not generally intended to
  be run by end-users.

Licensing
=========

``pypiserver`` contains a copy of bottle_ which is available under the
MIT license, and the remaining part is distributed under the zlib/libpng license.
See the ``LICENSE.txt`` file.


.. _bottle: http://bottlepy.org
.. _PyPA: https://www.pypa.io/en/latest/
.. _PyPI: https://pypi.org
.. _Warehouse: https://github.com/pypa/warehouse/
.. _twine: https://pypi.org/project/twine/
.. _pypi-uploader: https://pypi.org/project/pypi-uploader/
.. _python-pam: https://pypi.org/project/python-pam/
.. |travis-status| image:: https://travis-ci.org/pypiserver/pypiserver.svg
    :alt: Travis build status
    :scale: 100%
    :target: https://travis-ci.org/pypiserver/pypiserver

.. |pypi-ver| image::  https://img.shields.io/pypi/v/pypiserver.svg
    :target: https://pypi.org/project/pypiserver/
    :alt: Latest Version in PyPI

.. |python-ver| image:: https://img.shields.io/pypi/pyversions/pypiserver.svg
    :target: https://pypi.org/project/pypiserver/
    :alt: Supported Python versions

.. |proj-license| image:: https://img.shields.io/badge/license-BSD%2Bzlib%2Flibpng-blue.svg
    :target: https://raw.githubusercontent.com/pypiserver/pypiserver/master/LICENSE.txt
    :alt: Project License

.. |dependencies| image:: https://img.shields.io/requires/github/pypiserver/pypiserver.svg
    :target: https://requires.io/github/pypiserver/pypiserver/requirements/
    :alt: Dependencies up-to-date?
