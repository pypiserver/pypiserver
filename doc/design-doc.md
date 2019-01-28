# Pypiserver Design Doc

| | |
|----|----|
| Author | Matthew Planchard
| Date | 2019-01-28
| | |

Pypiserver version 2 will be a significant rewrite, with some major
new features and an improved architecture allowing much easier plugin
support. This design doc is intended to serve as a description and planning
document for both old and new features, while detailing some of the
architectural decisions around the new version.

## Guiding Principle for v2

Improve existing features and add new ones where it makes sense. Keep
pypiserver as easy to use if not easier. Make it easy to develop plugins
to expand functionality. Ensure that pypiserver is performant enough to
meet production requirements for large organizations.

## Major New or Improved Features

* **Async**
  pypiserver's core functionality, reading and writing package
  data, is fundamentally limited in its performance by the relatively slow
  speed of file and network I/O. The first version was built long before
  Python's async support, and a lot of effort has been expended over the years
  trying to improve performance when serving many packages or handling
  many connections. While asynchrony is not magic fairy dust for improving
  performance, it is very well suited for an application such as this, where
  a great deal of time is spent waiting for the filesystem or for the network.
* **Plugin Support**
  pypiserver will never be all things to all people, and that's okay! It will
  always be a minimal, performant, easy-to-use way to serve python packages.
  Even so, it should be easy for developers to extend pypiserver to do whatever
  they like with it. To enable that, this version will be designed with a
  plugin-oriented architecture from the beginning. Pluggable components will
  include storage, display, authentication, and authorization, minimally.
* **Out-of-the-box Authentication**
  Currently, `htpasswd` is used as an authentication shim for pypiserver.
  We will move to an authentication solution that does not require any
  third-party libraries and that is enabled out-of-the-box
* **User-level Authorization**
  Currently, authorization is an all-or-nothing affair. Any authenticated
  user may access packages at the permission level set globally for the
  server. In this version, we will enable the setting of specific permissions
  for specific users. We will also either plan for or go ahead and add
  the concept of roles or groups, to better manage the permissions of
  multiple users.
* **Command-line Introspection**
  Given our commitment to plugin support, we have to plan for a world where
  viewing available packages isn't necessarily a matter of running
  `ls ~/packages`. Both to support our extensible interface and to improve
  the user experience, the command-line interface for pypiserver will be
  significantly expanded, including commands to view and manage packages,
  users, and permissions.

## License Change

We will be updating our license from zlib/libpng to MIT. This is largely due
to the fact that the MIT license has become a defacto standard in the
open-source community, and we believe in open-source software being as
truly open as possible. The MIT license is pretty much as free as free can
be, and we want it to be as easy as possible for users to deploy pypiserver
in both organization and personal settings.

## Losses

No change is without its downsides. While we are trying to minimize them
as much as possible, some things must be left by the wayside as we move
forward.

* **Python 2 Support**
  We will always maintain a Python 2 compatible branch of pypiserver that will
  receive security updates and major bug fixes. However, Python 2
  is EOL at the end of this year (2019). This rewrite will probably
  be done before that, but it is not worth going through all the trouble of
  writing 2/3 compatible code for less than one year of total support.
  Supporting Python 2 would also limit us to third-party asynchronous solutions
  like Twisted.
* **Zero Dependencies**
  Unfortunately, I do not have the time to write my own HTTP server, and I
  am unwilling to inline `aiohttp`. As such, this version will have that as
  a dependency.
* **Standalone Distribution**
  When pypiserver was originally written, Python packaging and distribution
  was a nightmare. It was very difficult to get a package and its requirements
  distributed onto a system that did not have pip installed. Luckily, our
  world has changed significantly for the better, and it is now easy to use
  pip to download a package and all of its requirements, to be deployed on
  an offline server. As such, the necessity for a single, ready-to-use
  Python executable is not as extreme as it once was.
