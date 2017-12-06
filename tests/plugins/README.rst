===================
Test Plugins folder
===================

Test-project for evaluating stetuptools entry-points.
Run `/bin/test-plugins.sh` script to test them.


Files:
======

- ``pps_loadable.py``        : A plugin that when imported writes `/tmp/installable.txt`.
- ``pps_installable.sh``     : A plugin that when invoked its init-func writes `/tmp/installable.txt`.
- ``setup.py``               : The packaging descriptor.
- ``build/``                 : Receives the project's files.
- ``dist/``                  : Receives the build test-package.
- ``README.rst``             : This file.
