.. -*- mode: rst; coding: utf-8 -*-

==============================================================================
pypiserver - minimal PyPI server for use with pip/easy_install
==============================================================================

pypiserver is a minimal PyPI compatible server. It can be used to
serve a set of packages and eggs to easy_install or pip.

Installation and Usage/Quickstart
=================================
Run the following commands to get your PyPI server up and running::

  pip install pypiserver
  mkdir ~/packages
  # copy some source packages or eggs to this directory
  pypi-server -p 8080 -r ~/packages
  pip install -i http://localhost:8080/simple/ ...


Optional dependencies
=====================
- pypiserver ships with it's own copy of bottle. It's possible to use
  bottle with different wsgi servers. pypiserver chooses any of the
  following paste, cherrypy, twisted, wsgiref (part of python) if
  available.


Bugs
=============
- pypiserver doesn't support uploading files. One might also consider
  that a feature. scp provides a nice workaround.
