.. -*- mode: rst; coding: utf-8 -*-

==============================================================================
pypiserver - minimal PyPI server for use with pip/easy_install
==============================================================================


:Authors: Ralf Schmitt <ralf@systemexit.de>
:Version: 0.5.1
:Date:    2012-02-23
:Download: http://pypi.python.org/pypi/pypiserver
:Code: https://github.com/schmir/pypiserver


.. contents:: Table of Contents
  :backlinks: top


pypiserver is a minimal PyPI compatible server. It can be used to
serve a set of packages and eggs to easy_install or pip.

Installation and Usage/Quickstart
=================================
pypiserver will work with python 2.5, 2.6 and 2.7. Python 3 support
has been added with version 0.4.0.

Run the following commands to get your PyPI server up and running::

  pip install pypiserver
  mkdir ~/packages
  # copy some source packages or eggs to this directory
  pypi-server -p 8080 ~/packages
  pip install -i http://localhost:8080/simple/ ...

Alternative Installation as standalone script
=============================================
The git repository contains a 'pypi-server-standalone.py' script,
which is a single python file ready to be executed without any other
dependencies.

Run the following commands to download the script with wget::

  wget https://raw.github.com/schmir/pypiserver/standalone/pypi-server-standalone.py
  chmod +x pypi-server-standalone.py

or with curl::

  curl -O https://raw.github.com/schmir/pypiserver/standalone/pypi-server-standalone.py
  chmod +x pypi-server-standalone.py

The server can then be started with::

  ./pypi-server-standalone.py

Feel free to rename the script and move it into your $PATH.


Detailed Usage
=================================
pypi-server -h will print a detailed usage message::

  pypi-server [OPTIONS] [PACKAGES_DIRECTORY]
    start PyPI compatible package server serving packages from
    PACKAGES_DIRECTORY. If PACKAGES_DIRECTORY is not given on the
    command line, it uses the default ~/packages.  pypiserver scans this
    directory recursively for packages. It skips packages and
    directories starting with a dot.

  pypi-server understands the following options:

    -p PORT, --port PORT
      listen on port PORT (default: 8080)

    -i INTERFACE, --interface INTERFACE
      listen on interface INTERFACE (default: 0.0.0.0, any interface)

    --disable-fallback
      disable redirect to real PyPI index for packages not found in the
      local index

    --server METHOD
      use METHOD to run the server. Valid values include paste,
      cherrypy, twisted, gunicorn, gevent, wsgiref, auto. The
      default is to use "auto" which chooses one of paste, cherrypy,
      twisted or wsgiref.

    -r PACKAGES_DIRECTORY, --root PACKAGES_DIRECTORY
      [deprecated] serve packages from PACKAGES_DIRECTORY

  pypi-server -h
  pypi-server --help
    show this help message

  pypi-server --version
    show pypi-server's version

  pypi-server -U [OPTIONS] [PACKAGES_DIRECTORY]
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

  Visit http://pypi.python.org/pypi/pypiserver for more information.



Configuring pip/easy_install
============================
Always specifying the the pypi url on the command line is a bit
cumbersome. Since pypi-server redirects pip/easy_install to the
pypi.python.org index if it doesn't have a requested package, it's a
good idea to configure them to always use your local pypi index.

pip
-----
For pip this can be done by setting the environment variable
PIP_INDEX_URL in your .bashrc/.profile/.zshrc::

  export PIP_INDEX_URL=http://localhost:8080/simple/

or by adding the following lines to ~/.pip/pip.conf::

  [global]
  index-url = http://localhost:8080/simple/

easy_install
------------
For easy_install it can be configured with the following setting in
~/.pydistutils.cfg::

  [easy_install]
  index_url = http://localhost:8080/simple/

Managing the package directory
==============================
pypi-server's -U option makes it possible to search for updates of
available packages. It scans the package directory for available
packages and searches on pypi.python.org for updates. Without further
options 'pypi-server -U' will just print a list of commands which must
be run in order to get the latest version of each package. Output
looks like::

  checking 106 packages for newer version

  .........u.e...........e..u.............
  .....e..............................e...
  ..........................

  no releases found on pypi for PyXML, Pymacs, mercurial, setuptools

  # update raven from 1.4.3 to 1.4.4
  pip -q install --no-deps -i http://pypi.python.org/simple -d /home/ralf/packages/mirror raven==1.4.4

  # update greenlet from 0.3.3 to 0.3.4
  pip -q install --no-deps -i http://pypi.python.org/simple -d /home/ralf/packages/mirror greenlet==0.3.4

It first prints for each package a single character after checking the
available versions on pypi. A dot means the package is up-to-date, 'u'
means the package can be updated and 'e' means the list of releases on
pypi is empty. After that it show a pip command line which can be used
to update a one package. Either copy and paste that or run
"pypi-server -Ux" in order to really execute those commands. You need
to have pip installed for that to work however.

Specifying an additional '-u' option will also allow alpha, beta and
release candidates to be downloaded. Without this option these
releases won't be considered.


Optional dependencies
=====================
- pypiserver ships with it's own copy of bottle. It's possible to use
  bottle with different WSGI servers. pypiserver chooses any of the
  following paste, cherrypy, twisted, wsgiref (part of python) if
  available.

Source
===========
Source releases can be downloaded from
http://pypi.python.org/pypi/pypiserver

https://github.com/schmir/pypiserver carries a git repository of the
in-development version.

Use::

  git clone https://github.com/schmir/pypiserver.git

to create a copy of the repository, then::

  git pull

inside the copy to receive the latest version.


Bugs
=============
pypiserver does not implement the full API as seen on PyPI_. It
implements just enough to make easy_install and pip install work.

The following limitations are known:

- pypiserver doesn't support uploading files. One might also consider
  that a feature. scp provides a nice workaround.
- pypiserver doesn't implement the XMLRPC interface: pip search
  will not work.
- pypiserver doesn't implement the json based '/pypi' interface. pyg_
  uses that and will not work.

Please use github's bugtracker
https://github.com/schmir/pypiserver/issues if you find any other
bugs.


License
=============
pypiserver contains a copy of bottle_ which is available under the
MIT license::

  Copyright (c) 2010, Marcel Hellkamp.

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in all
  copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
  SOFTWARE.


The remaining part is distributed under the zlib/libpng license::

  Copyright (c) 2011 Ralf Schmitt

  This software is provided 'as-is', without any express or implied
  warranty. In no event will the authors be held liable for any damages
  arising from the use of this software.

  Permission is granted to anyone to use this software for any purpose,
  including commercial applications, and to alter it and redistribute it
  freely, subject to the following restrictions:

  1. The origin of this software must not be misrepresented; you must not
     claim that you wrote the original software. If you use this software
     in a product, an acknowledgment in the product documentation would be
     appreciated but is not required.

  2. Altered source versions must be plainly marked as such, and must not be
     misrepresented as being the original software.

  3. This notice may not be removed or altered from any source
     distribution.


Similar Projects
====================
There are lots of other projects, which allow you to run your own
PyPI server. If pypiserver doesn't work for you, try one of the
following alternatives:

chishop (http://pypi.python.org/pypi/chishop)
  a django based server, which also allows uploads

simplepypi (http://pypi.python.org/pypi/simplepypi)
  a twisted based solution, which allows uploads

ClueReleaseManager (http://pypi.python.org/pypi/ClueReleaseManager)
  Werkzeug based solution, allows uploads

haufe.eggserver (http://pypi.python.org/pypi/haufe.eggserver)
  GROK/Zope based, allows uploads

scrambled (http://pypi.python.org/pypi/scrambled)
  doesn't require external dependencies, no uploads.

EggBasket (http://pypi.python.org/pypi/EggBasket)
  TurboGears based, allows uploads


Changelog
=========
0.5.1 (2012-02-23)
------------------
- make 'pypi-server -U' compatible with pip 1.1

0.5.0 (2011-12-05)
------------------
- make setup.py install without calling 2to3 by changing source code
  to be compatible with both python 2 and python 3. We now ship a
  slightly patched version of bottle. The upcoming bottle 0.11
  also contains these changes.
- make the single-file pypi-server-standalone.py work with python 3

0.4.1 (2011-11-23)
------------------
- upgrade bottle to 0.9.7, fixes possible installation issues with
  python 3
- remove dependency on pkg_resources module when running
  'pypi-server -U'

0.4.0 (2011-11-19)
------------------
- add functionality to manage package updates
- updated documentation
- python 3 support has been added

0.3.0 (2011-10-07)
------------------
- pypiserver now scans the given root directory and it's
  subdirectories recursively for packages. Files and directories
  starting with a dot are now being ignored.
- /favicon.ico now returns a "404 Not Found" error
- pypiserver now contains some unit tests to be run with tox

0.2.0 (2011-08-09)
------------------
- better matching of package names (i.e. don't install package if only
  a prefix matches)
- redirect to the real pypi.python.org server if a package is not found.
- add some documentation about configuring easy_install/pip

0.1.3 (2011-08-01)
------------------
- provide single file script pypi-server-standalone.py
- better documentation

0.1.2 (2011-08-01)
------------------
- prefix comparison is now case insensitive
- added usage message
- show minimal information for root url

0.1.1 (2011-07-29)
------------------
- don't require external dependencies

0.1.0 (2011-07-29)
------------------
- initial release


.. _bottle: http://bottlepy.org
.. _PyPI: http://pypi.python.org
.. _pyg: http://pypi.python.org/pypi/pyg
