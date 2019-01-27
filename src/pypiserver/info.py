"""Package information."""

__pkg_name__ = 'pypiserver'
__author__ = "Matthew Planchard"
__author_email__ = "msplanchard@gmail.com"
__license__ = "MIT"
__url__ = "https://github.com/pypiserver/pypiserver"

__short_description__ = "Pip-compatible python package server"
__long_description__ = (
    "Pypiserver provides a pip-compatible python package server, with "
    "optional support for authentication. It provides a plugin-oriented "
    "architecture to make it as easy as possible to add new features. "
    "Check us out on GitHub. Contributions are always welcome!"
)

__version_info__ = (2, 0, 0)
__version__ = ".".join(str(v) for v in __version_info__)
__build_tag__ = "dev"
__post_ver__ = 0
__full_version__ = ".".join((__version__, f"{__build_tag__}{__post_ver__}"))
