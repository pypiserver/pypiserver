#! /usr/bin/env python
"""standalone pypi-server, version @VERSION@"""

sources = """
@SOURCES@"""

import sys, base64, zlib, cPickle

sources = cPickle.loads(zlib.decompress(base64.decodestring(sources)))


class DictImporter(object):
    sources = sources

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

        exec co in module.__dict__
        return sys.modules[fullname]

    def get_source(self, name):
        res = self.sources.get(name)
        if res is None:
            res = self.sources.get(name + '.__init__')
        return res


importer = DictImporter()
sys.meta_path.append(importer)

if __name__ == "__main__":
    from pypiserver.core import main
    main()
