Changelog
=========

1.4.2 (2020-10-10)
------------------

- FIX: The entrypoint for the Dockerfile was failing when called with no
  arguments (#344, thanks @elfjes!)

1.4.1 (2020-10-05)
------------------

- FIX: The entrypoint for the Dockerfile no longer tries to `chown` the
  entire `/data` directory, instead limiting itself just to `/data/packages`
  as before (reported by @stephen-dexda in #341, thanks!).

1.4.0 (2020-10-03)
------------------

- DOC: Add docker-compose example with HTTPS configuration using Traefix (#295, thanks @Lauszus!)
- DOC: Add link to zulip chat to README (aa2d78c)
- DOC: Documentation for running as a service in windows (#316, thanks @kodaman2!)
- DOC: Fix typo in README HTML (#303, thanks @Gerardwx!)
- DOC: Moved flask-pypi-proxy and pip2pi to a new "Unmaintained or archived" section (#326, thanks @Luttik!)
- DOC: Slightly clarify the relationship to warehouse. (#308, thanks @Julian!)
- ENH: Add ignore list for the update command (#298, thanks @peter-slovak!)
- ENH: Add official support and testing for Python 3.8 (#292) for Python 3.8 compatibility
- ENH: Allow configuration of logging stream (#334, thanks @elfjes)
- ENH: Include watchdog to enable caching in docker image (#323, thanks @johnchildren!)
- FIX: Cherrypy import for newer versions of cherrypy in vendored bottle.py (#301, thanks @TiemenSch!)
- FIX: Improved permissions management in Dockerfile (#330, thanks @normoes)
- FIX: Usage of string formatting in HTTPError (#310, thanks @micahjsmith!)
- MAINT: Update bottle to [0.12.18](https://github.com/bottlepy/bottle/releases/tag/0.12.18) (#290)
- MAINT: Use Python 3.8 in Dockerfile (#330, thanks @normoes)
- MAINT: bump version of passlib from 1.7.1 to 1.7.2 in Docker requirements (#293)
- MAINT: drop official support for Python 3.4 (#321)

1.3.2 (2020-01-11)
------------------

- ENH: The Dockerfile used for the official Docker images now uses Python 3.6
  rather than Python 2.7 (#284, thanks @etene!)
- ENH: The `welcome.html` page has been updated to provide more metadata
  and be more HTML-standards compliant (#283, thanks @maggyero!)
- FIX: the `pypi-server -U` command no longer fails when run inside the
  Docker container (thanks to @mkolb-navican for reporting in #264)
- FIX: The `remove_pkg` API action now removes any extant instances of a
  package name-version combination, not just the first one found. This means
  that now, for example, if a `.whl` and `.tar.gz` file exist for the
  requested package name and version, both will be removed (thanks to
  @esciara for reporting in #268)
- FIX: include missing `simple/` path on a URL in the example pip commands
  on the `welcome.html` page (@276, thanks @maggyero!)
- DOC: more consistent and accurate documentation for pip commands provided
  on the `welcome.html` page (#278, thanks @maggyero!)
- DOC: fixes to the README to make it easier for people to use pypiserver
  behind an apache webserver (#289, thanks @Helveg!)


1.3.1 (2019-09-10)
------------------

- FIX: previously, it was possible to upload packages with hashing algorithms
  other than md5, but downloading them again with pip was impossible due to
  incorrect truncation of the hash. This has been fixed! (Thanks
  @ArneBachmann for figuring out what was wrong and reporting the issue
  in #265).
- FIX: argument parsing would previously fail for the short form of
  ``--help``, due an incorrect operator used during comparison (thanks to
  @maggyero, #271)
- DOC: significant improvements to formatting and consistency in the README
  (thanks to @maggyero, #270)

1.3.0 (2019-05-05)
------------------

- ENH: pypiserver now consistently and correctly handles the `X-Forwarded-Host`
  header to allow for alternative base URLs (#248, resolves #155, thanks
  @kujyp for an excellent first-time contribution!)
- DOC: significantly more information added to the `docker-compose.yml`
  example, including recipes for various configuration options (thanks
  @jetheurer for pointing out the errors in the existing docs, #243!)
- DOC: removed outdated suggestion to serve the packages data directly via
  a webserver and replaced with information about setting up nginx
  caching (thanks @RiceKab for bringing the issue to our attention, #232)


1.2.7 (2019-01-31)
------------------

- FIX: bcrypt is now *properly* installed in the Docker image, and our
  automated tests now do a better job of making sure authentication and
  uploads work as expected in Docker (thanks @ronneke1996, #239; also
  thanks @kellycampbell, #235 for an alternate approach that wound up
  being unused but is still appreciated!)

1.2.6 (2019-01-26)
------------------

- SEC: mitigate potential CRLF injection attacks from malicious URLs
  (thanks @samwcyo, #237)

1.2.5 (2018-11-11)
------------------

- FIX: bcrypt is now installed into the Docker image, which allows
  passlib to work like it should (thanks @Diftraku, #224)

- MAINT: integration tests with ``twine`` have been updated to use the
  command-line interface rather than the internal API, which should
  make them more resilient over time (#226)

1.2.4 (2018-08-06)
------------------

- FIX: the command to download new versions of available packages now
  works with ``pip`` >= 10.0 (thanks @elboerto, #215)

1.2.3 (2018-08-04)
------------------

- MAINT: Remove broken downloads badge (thanks @hugovk, #209)

- ENH: Improved Dockerfile and ``docker-compose`` example, docs for using
  the docker image, automatic docker builds

1.2.2 (2018-06-12)
------------------

- FIX: update fallback URL to https://pypi.org/simple since pypi.python.org
  has shut down

- FIX: updated tests to use ``Popen`` rather than ``pip.main()`` given its
  removal in pip version 10.0

- DOC: scrubbed docs of links to pypi.python.org

- DEPRECATION: Drop support for Python 3.3 (thanks @hugovk, #198)


1.2.1 (2017-11-29)
------------------

- FIX propagation of certain ``pypiserver`` settings via a ``paste.ini`` config
  file (thanks @luismsgomes, #156)

- FIX update default fallback URL to be https for compliance with PyPI
  (thanks @uSpike, #182)

- FIX resolved a regression preventing spinning up multiple pypiservers
  via a paste config (thanks @bertjwregeer, #173)

- FIX cmdline parsing of stray comparison consuming many flags (e.g. ``--help``),
  and docs about ``auther``
  - (thanks to @sakurai-youhei, #162).

- Travis CI testing for Python 3.6 and pypy3 (#183)

- Several documentation improvements (thanks @tescalada, #166, #161, #172 and
  @axnsan12, #190)

1.2.0 (2016-06-25)
------------------
"Brexit": Normalize and stop legacy support.

- Less rigorous support for ``python-2 < 2.7`` and ``python-3 < 3.3``.
- Package normalizations and :pep:`503` updates:
  - Package names are normalized: convert all characters to lower-case
    and replace any of ``[-_.]`` with a dash(``'-'``).
  - The simple index only lists normalized package names.
  - Any request for a non-normalized package name is redirected to
    the normalized name.
  - URLs are redirected unless they end in ``'/'`` (expect packages themselves).
  - (thanks to @dpkp, #38, #139, #140)

- Added ``pip search`` support.
  - (thanks to @blade2005, #80, #114)

- FIX startup regressions for other WSGI-servers, introduced by previous ``v1.1.10``.
  - (thanks to @virtuald, @Oneplus, @michaelkuty, @harcher81, @8u1a,
    #117, #122, #124/#127/#128)

- FIX over-writing of packages even when without ``--overwrite`` flag.
  - (thanks to @blade2005, #113)

- Fixes for *paste*, *gunicorn* and other *WSGI* servers.
  - (thanks to @corywright, @virtuald, @montefra, #112, #118, #119)

- Updates and fixes needed due to changes in dependent libraries.
  - (thanks @dpkp, #120/#121, #129, #141/#142)

- Add cache for speeding up GPG signatures.
  - sthanks to @virtuald, #116)

- Other minor fixes and improvements.
  - (thanks to @bibby, @Oneplus, @8u1a, #129, #131)

- TravisCI-test against *python-3.5*.
  - (#107, #108, #110)

- docs:

  - Provide samples for *Automated Startup* (``systemd`` & ``hypervisor``).
    (thanks to @ssbarnea, #137, #146)

  - Add usage instructions for related project ``pypi-uploader``.
    (thanks to @ssbarnea & @bibby, #147)

  - doc: Provide sample-code to authenticate using ``/etc/passwds`` file
    via *pam* modules in Unix.
    - (thanks to @blade2005, #149, #151-#153)

  - Improved API usage instructions.
  - Detailed changes recorded in `Github's milestone 1.2.0
    <https://github.com/pypiserver/pypiserver/milestones/M1.2.0>`_.


1.1.10 (2016-01-19)
-------------------
Serve 1000s of packages, PGP-Sigs, skip versions starting with 'v'.

+ #101: Speed-up server by (optionally) using the `watchdog` package
  to cache results, serve packages directly from proxying-server (*Apache* ,
  *nginx*), and pre-compile regexes (thanks @virtuald).
- #106: Support uploading PGP-signatures (thanks @mplanchard).
- Package-versions parsing modifications:

  - #104: Stopped parsing invalid package-versions prefixed with `v`; they are
    invalid according to :pep-reference:`0440` (thanks @virtuald &
    @stevejefferiesIDBS).
  - Support versions with epochs separated by `!` like `package-1!1.1.0`.
  - #102: FIX regression on uploading packages with `+` char in their version
    caused by recent bottle-upgrade.
- #103: Minor doc fixes (thanks @MichaelSchneeberger).


1.1.9 (2015-12-21)
------------------
"Ssss-elections" bug-fix & maintenance release.

- Upgrade bottle 1.11.6-->1.13-dev.

  - Fixes `MAX_PARAM` limiting dependencies(#82)

- Rework main startup and standalone:

  - New standalone generation based on ZIPed wheel archive.
  - Replace all sys.module mechanics with relative imports.
  - Fix gevent monkeypatching (#49).
  - Simplify definition of config-options on startup.
  - TODO: Move startup-options validations out of `main()` and
    into `pypiserver.core`
    package, to validate also start-up from API-clients.

- #53: Like PyPI, HREF-links now contain package's md5-hashes in their fragment.
  Add `--hash_algo` cmd-line option to turn-off or specify other *hashlib*
  message-digest algorithms (e.g. `sha256` is a safer choice, set it to `off`
  to avoid any performance penalty if hosting a lot of packages).

- #97: Add `--auther` non cmd-line startup-option to allow for alternative
  authentication methods (non HtPasswdFile-based one) to be defined by
  API-clients (thanks @Tythos).

- #91: Attempt to fix register http failures (thanks to @Tythos and @petri).

  - Test actual clients (ie `pip`, `Twine`, `setuptools`).
  - Test spurious `setuptools` failures.
  - NOT FIXED!  Still getting spurious failures.

- Various other fixes:

  - #96: Fix program's requirement (i.e. add passlib as extra-requirement).
    provide requirements files also for developers.
  - logging: Send also bottle `_stderr` to logger; fix logger names.
  - #95: Add missing loop-terminators in bottle-templates (thanks to @bmflynn).



1.1.8 (2015-09-15)
------------------
"Finikounda" release.

- Allow un-authenticated uploads (no htpasswd file) (#55).
- Fixes on package-name handling (#85 and #88, #89).
- Respect logging cmd-line options (#81).
- Add TCs for standalone script and other build-issues (#92)
- See milestone:M1.1.8 on github for all fixes included.


1.1.7 (2015-03-8)
-----------------
1st release under cooperative ownership:

- #65, #66: Improve Auth for private repos by supporting i
  password protected package listings and downloads,
  in addition to uploads (use the -a, --authenticate option
  to specify which to protect).
- #67: Add cache-control http-header, reqed by pip.
- #56, #70: Ignore non-packages when serving.
- #58, #62: Log all http-requests.
- #61: Possible to change welcome-msg.
- #77, #78: Avoid XSS by generating web-content with SimpleTemplate
  instead of python's string-substs.
- #38, #79: Instruct to use --extra-index-url for misspelled dependencies to work,
  reorganize README instructions.


1.1.6 (2014-03-05)
------------------
- remove --index-url cli parameter introduced in 1.1.5

1.1.5 (2014-01-20)
------------------
- only list devpi-server and proxypypi as alternatives
- fix wheel file handling for certain wheels
- serve wheel files as application/octet-stream
- make pypiserver executable from wheel file
- build universal wheel
- remove scripts subdirectory
- add --index-url cli parameter

1.1.4 (2014-01-03)
------------------
- make pypiserver compatible with pip 1.5
  (https://github.com/pypiserver/pypiserver/pull/42)

1.1.3 (2013-07-22)
------------------
- make guessing of package name and version more robust

1.1.2 (2013-06-22)
------------------
- fix "pypi-server -U" stable/unstable detection, i.e. do not
  accidentally update to unstable packages

1.1.1 (2013-05-29)
------------------
- add 'overwrite' option to allow overwriting existing package
  files (default: false)
- show names with hyphens instead of underscores on the "/simple"
  listing
- make the standalone version work with jython 2.5.3
- upgrade waitress to 0.8.5 in the standalone version
- workaround broken xmlrpc api on pypi.python.org by using HTTPS

1.1.0 (2013-02-14)
------------------
- implement multi-root support (one can now specify multiple package
  roots)
- normalize pkgnames, handle underscore like minus
- sort files by their version, not alphabetically
- upgrade embedded bottle to 0.11.6
- upgrade waitress to 0.8.2 in the standalone script
- merge vsajip's support for verify, doc_upload and remove_pkg

1.0.1 (2013-01-03)
------------------
- make 'pypi-server -Ux' work on windows
  ('module' object has no attribute 'spawnlp',
  https://github.com/pypiserver/pypiserver/issues/26)
- use absolute paths in hrefs for root view
  (https://github.com/pypiserver/pypiserver/issues/25)
- add description of uploads to the documentation
- make the test suite work on python 3
- make pypi-server-standalone work with python 2.5

1.0.0 (2012-10-26)
------------------
- add passlib and waitress to pypi-server-standalone
- upgrade bottle to 0.11.3
- Update scripts/opensuse/pypiserver.init
- Refuse to re upload existing file
- Add 'console_scripts' section to 'entry_points', so
  'pypi-server.exe' will be created on Windows.
- paste_app_factory now use the the password_file option to create the
  app. Without this the package upload was not working.
- Add --fallback-url argument to pypi-server script to make it
  configurable.

0.6.1 (2012-08-07)
------------------
- make 'python setup.py register' work
- added init scripts to start pypiserver on ubuntu/opensuse

0.6.0 (2012-06-14)
------------------
- make pypiserver work with pip on windows
- add support for password protected uploads
- make pypiserver work with non-root paths
- make pypiserver 'paste compatible'
- allow to serve multiple package directories using paste

0.5.2 (2012-03-27)
------------------
- provide a way to get the WSGI app
- improved package name and version guessing
- use case insensitive matching when removing archive suffixes
- fix pytz issue #6

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
