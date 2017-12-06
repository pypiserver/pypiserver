#! /usr/bin/env python

from setuptools import setup

setup(name='pypiserver-test-plugins',
      description="test-plugins for PypiServer",
      long_description="""
          Pip-installs 2 entry-points:
          - loadable:    that on *load* writes `/tmp/loaded.txt` file, and
          - installable: that on *instal* writes `/tmp/installed.txt` file.
      """,
      version='0.0.0',
      maintainer='nobody',
      maintainer_email='nobody@nowhere.go',
      zip_safe=True,
      py_modules=['pps_loadable', 'pps_installable'],
      install_requires='pypiserver',
      entry_points={
        'pypiserver.plugins': [
            'loadable = pps_loadable',                   ## Load only.
            'installable = pps_installable:init_plugin', ## Load & install.
        ]
      },
      options={
          'bdist_wheel': {'universal': True},
      },
      platforms=['any'],
      )
