"""Tests for optional dependency loading."""

import os
import pathlib
import subprocess
import sys


def test_unauthenticated_commands_do_not_import_passlib(
    tmp_path: pathlib.Path,
) -> None:
    passlib_dir = tmp_path / "passlib"
    passlib_dir.mkdir()
    (passlib_dir / "__init__.py").write_text("", encoding="utf-8")
    (passlib_dir / "apache.py").write_text(
        'raise RuntimeError("passlib must not be imported")',
        encoding="utf-8",
    )

    env = os.environ.copy()
    python_path = env.get("PYTHONPATH")
    env["PYTHONPATH"] = os.pathsep.join(
        path for path in (str(tmp_path), python_path) if path
    )
    commands = (
        ("-c", "import pypiserver"),
        (
            "-c",
            "from pypiserver.config import Config; Config.from_args(['run'])",
        ),
        (
            "-c",
            "from pypiserver.config import Config; "
            "Config.from_args(['run', '-a', '.', '-P', '.'])",
        ),
        (
            "-c",
            "from pypiserver.config import Config; Config.from_args(['update'])",
        ),
        (
            "-c",
            "from pypiserver.config import Config; "
            "Config.default_with_overrides(password_file='ignored', "
            "auther=lambda _user, _password: True)",
        ),
        ("-m", "pypiserver", "--help"),
    )
    for command in commands:
        result = subprocess.run(
            [sys.executable, *command],
            cwd=pathlib.Path(__file__).parent.parent,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, (command, result.stderr)
