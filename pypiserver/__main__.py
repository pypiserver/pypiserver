if __name__ == "__main__":
    if __package__ == "":  # running as python pypiserver-...whl/pypiserver?
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from pypiserver import core
    core.main()
