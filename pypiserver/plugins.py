"""Plugins are setuptools entrypoints that are invoked at startup that a
developer may use to extend the behaviour of pypiserver. A plugin for example
may add an additional Backend to the system. A plugin is currently called
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
An example plugin is given below that enables two custom backends.
"""
from pypiserver.backend import Backend


class MySpecialBackend(Backend):
    def __init__(self, hash_algo, frobnicate):
        super().__init__(hash_algo)
        self.frobnicate = frobnicate

    @classmethod
    def from_config(cls, config):
        return cls(config.hash_algo, config.frobnicate)

    # Implement the required Backend methods here
    ...


class MyOtherBackend(Backend):
    def __init__(self, config):
        super().__init__(hash_algo=config.hash_algo)


# register this as a setuptools entrypoint under the 'pypiserver.plugin' key
def my_plugin(add_argument, backends, **_):
    add_argument(
        "--frobnicate",
        action="store_true",
        help="Frobnicate for my special backend",
    )
    backends.update(
        {
            "my-special-backend": MySpecialBackend.from_config,
            "my-other-backend": MyOtherBackend,
        }
    )
