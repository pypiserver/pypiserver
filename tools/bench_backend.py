"""Measure backend lookup cost. Usage:
python -m tools.bench_backend --counts 1000 10000 --rounds 50
"""

import argparse
import importlib.util
import statistics
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from pypiserver import backend as patched


def load_baseline(directory):
    path = directory / "baseline_backend.py"
    path.write_bytes(
        subprocess.check_output(
            ["git", "show", "70648db:pypiserver/backend.py"],
            cwd=Path(__file__).resolve().parents[1],
        )
    )
    spec = importlib.util.spec_from_file_location(
        "pypiserver._baseline_backend", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def backend_instance(backend_type, config):
    backend = backend_type(config)
    try:
        yield backend
    finally:
        if hasattr(backend, "cache_manager"):
            observer = backend.cache_manager.observer
            observer.stop()
            observer.join()


def materialize(packages):
    # Consume the old iterator without copying an already materialized result.
    return packages if isinstance(packages, list) else list(packages)


def measure(backend_type, directory, rounds):
    config = SimpleNamespace(roots=[directory], hash_algo=None)
    count = int(directory.name)
    lookups = (
        ("get_by_relfn (first)", "pkg0-1.0.0-py3-none-any.whl", True),
        (
            "get_by_relfn (last)",
            f"packages/last/pkg{count - 1}-1.0.0-py3-none-any.whl",
            True,
        ),
        ("get_by_relfn (missing)", "missing-pkg", False),
    )
    samples = {
        "get_all_packages (cold)": [],
        "get_all_packages (warm)": [],
        "find_project_packages": [],
    }
    for name, _, _ in lookups:
        samples[name] = []
    for _ in range(rounds):
        with backend_instance(backend_type, config) as backend:
            start = time.perf_counter()
            packages = materialize(backend.get_all_packages())
            samples["get_all_packages (cold)"].append(
                time.perf_counter() - start
            )
            if len(packages) != count:
                raise ValueError("Unexpected package count")
            if (
                packages[0].relfn_unix != lookups[0][1]
                or packages[-1].relfn_unix != lookups[1][1]
            ):
                raise ValueError(
                    "Unexpected first or last package in scan order"
                )
            del packages

            start = time.perf_counter()
            packages = materialize(backend.get_all_packages())
            samples["get_all_packages (warm)"].append(
                time.perf_counter() - start
            )
            del packages

            start = time.perf_counter()
            project = materialize(backend.find_project_packages("pkg42"))
            samples["find_project_packages"].append(time.perf_counter() - start)
            if len(project) != 1 or project[0].pkgname_norm != "pkg42":
                raise ValueError("Unexpected project lookup result")

            lookup = getattr(backend, "get_by_relfn", None)
            for name, filename, expected_hit in lookups:
                start = time.perf_counter()
                if lookup is None:
                    # The original server_static stopped at the first match.
                    for package in backend.get_all_packages():
                        if package.relfn_unix == filename:
                            break
                    else:
                        package = None
                else:
                    package = lookup(filename)
                samples[name].append(time.perf_counter() - start)
                expected = filename if expected_hit else None
                if (
                    package.relfn_unix if package is not None else None
                ) != expected:
                    raise ValueError(
                        f"Unexpected relative-path lookup result: {name}"
                    )
    return {
        name: statistics.median(times) * 1000 for name, times in samples.items()
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--counts", type=int, nargs="+", default=[1000, 10000])
    parser.add_argument("--rounds", type=int, default=50)
    args = parser.parse_args()
    if args.rounds < 1 or min(args.counts) <= 42:
        parser.error("rounds must be positive and counts must include pkg42")

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        baseline = load_baseline(root)
        for count in args.counts:
            directory = root / str(count)
            packages = directory / "packages"
            last = packages / "last"
            last.mkdir(parents=True)
            (directory / "pkg0-1.0.0-py3-none-any.whl").touch()
            for i in range(1, count - 1):
                (packages / f"pkg{i}-1.0.0-py3-none-any.whl").touch()
            (last / f"pkg{count - 1}-1.0.0-py3-none-any.whl").touch()

        backends = ["SimpleFileBackend"]
        if patched.ENABLE_CACHING:
            backends.append("CachingFileBackend")
        else:
            print(
                "CachingFileBackend requires the cache extra.", file=sys.stderr
            )

        results = []
        for module in (baseline, patched):
            timings = {}
            for name in backends:
                for count in args.counts:
                    measurements = measure(
                        getattr(module, name), root / str(count), args.rounds
                    )
                    for operation, milliseconds in measurements.items():
                        timings[name, count, operation] = milliseconds
            results.append(timings)

    before, after = results
    print("| bench | N | baseline_ms | patched_ms | speedup |")
    print("|---|---:|---:|---:|---:|")
    for (name, count, operation), baseline_ms in before.items():
        patched_ms = after[name, count, operation]
        print(
            f"| {name}.{operation} | {count} | {baseline_ms:.6f} | "
            f"{patched_ms:.6f} | {baseline_ms / patched_ms:.2f}x |"
        )


if __name__ == "__main__":
    main()
