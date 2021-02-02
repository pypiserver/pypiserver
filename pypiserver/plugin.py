""" NOT YET IMPLEMENTED

Plugins are callable setuptools entrypoints that are invoked at startup that
a developer may use to extend the behaviour of pypiserver. A plugin for example
may add an additional Backend to the system. A plugin will be called
with the following keyword arguments

* app: the Bottle App object
* add_argument: A callable for registering command line arguments for your
    plugin using the argparse cli library
* backends: A Dict[str, callable] object that you may register a backend to.
    The key is the identifier for the backend in the `--backend` command line
    argument.
    The callable must take a single argument `config` as a Configuration object
    and return a Backend instance. It may be the class constructor or a factory
    function to construct a Backend object

In the future, the plugin callable may be called with additional keyword
arguments, so a plugin should accept a **kwargs variadic keyword argument.
"""
from pypiserver.backend import SimpleFileBackend, CachingFileBackend
from pypiserver import get_file_backend

DEFAULT_PACKAGE_DIRECTORIES = ["~/packages"]


# register this as a setuptools entrypoint under the 'pypiserver.plugin' key
def my_plugin(add_argument, backends, **_):
    add_argument(
        "package_directory",
        default=DEFAULT_PACKAGE_DIRECTORIES,
        nargs="*",
        help="The directory from which to serve packages.",
    )
    backends.update(
        {
            "auto": get_file_backend,
            "simple-dir": SimpleFileBackend,
            "cached-dir": CachingFileBackend,
        }
    )
