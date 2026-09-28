import importlib.util
import pathlib
import typing as t

import pypiserver


def test_release_script_reads_current_version_metadata() -> None:
    script = pathlib.Path(__file__).parents[1] / "bin" / "bumpver.py"
    spec = importlib.util.spec_from_file_location("pypiserver_bumpver", script)
    assert spec is not None
    assert spec.loader is not None

    module = t.cast(t.Any, importlib.util.module_from_spec(spec))
    spec.loader.exec_module(module)

    assert list(module.bumpver("")) == [
        pypiserver.__version__,
        pypiserver.__updated__,
        pypiserver.__updated__.split()[0],
    ]
