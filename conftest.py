import sys
import httplib


def pytest_configure(config):
    if hasattr(sys, "pypy_version_info"):
        # mechanize (as included by twill) calls this
        httplib.HTTPResponse._decref_socketios = lambda self: None
