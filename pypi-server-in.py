#! /usr/bin/env python
"""standalone pypi-server, version @VERSION@"""

sources = """
@SOURCES@"""

import sys, base64, zlib


class DictImporter(object):
    sources = None

    def find_module(self, fullname, path=None):
        if fullname in self.sources:
            return self
        if fullname + '.__init__' in self.sources:
            return self
        return None

    def load_module(self, fullname):
        try:
            s = self.sources[fullname]
            is_pkg = False
        except KeyError:
            s = self.sources[fullname + '.__init__']
            is_pkg = True

        co = compile(s, fullname, 'exec')
        module = sys.modules.setdefault(fullname, type(sys)(fullname))
        module.__file__ = __file__
        module.__loader__ = self
        if is_pkg:
            module.__path__ = [fullname]

        do_exec(co, module.__dict__)
        return sys.modules[fullname]

    def get_source(self, name):
        res = self.sources.get(name)
        if res is None:
            res = self.sources.get(name + '.__init__')
        return res


if sys.version_info >= (3, 0):
    import pickle
    exec("def do_exec(co, loc): exec(co, loc)\n")
    sources = sources.encode("ascii")  # ensure bytes
    d = zlib.decompress(base64.decodebytes(sources))
    sources = pickle.loads(zlib.decompress(base64.decodebytes(sources)), encoding="utf-8")
else:
    import cPickle as pickle
    exec("def do_exec(co, loc): exec co in loc\n")
    sources = pickle.loads(zlib.decompress(base64.decodestring(sources)))

importer = DictImporter()
importer.sources = sources
sys.meta_path.append(importer)

if __name__ == "__main__":
    from pypiserver.core import main
    main()
