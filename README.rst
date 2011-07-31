.. -*- mode: rst; coding: utf-8 -*-

==============================================================================
pypiserver - minimal PyPI server for use with pip/easy_install
==============================================================================

:Authors: Ralf Schmitt <ralf@systemexit.de>

.. contents:: Table of Contents
  :backlinks: top


pypiserver is a minimal PyPI compatible server. It can be used to
serve a set of packages and eggs to easy_install or pip.

Installation and Usage/Quickstart
=================================
pypiserver will work with python 2.5, 2.6 and 2.7. It will *not* work
with python versions >= 3 or < 2.5.

Run the following commands to get your PyPI server up and running::

  pip install pypiserver
  mkdir ~/packages
  # copy some source packages or eggs to this directory
  pypi-server -p 8080 ~/packages
  pip install -i http://localhost:8080/simple/ ...


Detailed Usage
=================================
pypi-server -h will print a detailed usage message::

  pypi-server [OPTIONS] [PACKAGES_DIRECTORY]
    start PyPI compatible package server serving packages from
    PACKAGES_DIRECTORY. If PACKAGES_DIRECTORY is not given on the
    command line, it uses the default ~/packages.

  pypi-server understands the following options:

    -p PORT, --port PORT
      listen on port PORT (default: 8080)

    -i INTERFACE, --interface INTERFACE
      listen on interface INTERFACE (default: 0.0.0.0, any interface)

    -r PACKAGES_DIRECTORY, --root PACKAGES_DIRECTORY
      [deprecated] serve packages from PACKAGES_DIRECTORY

    --server METHOD
      use METHOD to run the server. Valid values include paste,
      cherrypy, twisted, gunicorn, gevent, wsgiref, auto. The
      default is to use "auto" which chooses one of paste, cherrypy,
      twisted or wsgiref.

  pypi-server -h
  pypi-server --help
    show this help message

  pypi-server --version
    show pypi-server's version

  Visit http://pypi.python.org/pypi/pypiserver for more information.


Optional dependencies
=====================
- pypiserver ships with it's own copy of bottle. It's possible to use
  bottle with different wsgi servers. pypiserver chooses any of the
  following paste, cherrypy, twisted, wsgiref (part of python) if
  available.


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

scrambled (http://pypi.python.org/pypi/scrambled)
  doesn't require external dependencies, no uploads.

EggBasket (http://pypi.python.org/pypi/EggBasket)


.. _bottle: http://bottlepy.org
.. _PyPI: http://pypi.python.org
.. _pyg: http://pypi.python.org/pypi/pyg
.. _chishop: http://pypi.python.org/pypi/chishop
.. _simplepypi:
