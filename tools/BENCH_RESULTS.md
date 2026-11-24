# Backend package index benchmark

The index is used by **`CachingFileBackend` only**. `SimpleFileBackend` keeps
rescanning on every call, so there is nothing to measure for it any more: a root
`st_mtime_ns` token cannot see a package dropped into a subdirectory, and reusing
the memoised `PkgFile` objects would serve a stale digest after an in-place
replace. Both cases are covered by regression tests instead
(`test_simple_backend_sees_package_added_to_subdirectory`,
`test_simple_backend_digest_reflects_in_place_replace`).

Run in the repository virtual environment on Windows with
`python -m tools.bench_backend --counts 1000 5000`. The optional cache backend
used `watchdog==6.0.0` from `.venv/t1-bench-deps` through the benchmark process's
`PYTHONPATH`.

Values are medians of 50 rounds in milliseconds. All measurements of
`git show 70648db:pypiserver/backend.py` ran before measurements of the branch
working tree on the same package directories. Each cold call uses a fresh
backend. The warm call and both lookups reuse that instance. The original
relative-path lookup stops at the first matching file, as the original download
route did. For each N, pkg0 is the first match, pkg{N-1} is the last match after a
full scan, and missing-pkg is a no-match full scan.

The first warm call on a fresh backend still builds the index, which costs about
6 % more than the single scan the baseline performed. Everything after that is a
hash lookup.

| bench | N | baseline_ms | patched_ms | speedup |
|---|---:|---:|---:|---:|
| CachingFileBackend.get_all_packages (cold) | 1000 | 52.551550 | 56.039800 | 0.94x |
| CachingFileBackend.get_all_packages (warm) | 1000 | 0.012100 | 0.001150 | 10.52x |
| CachingFileBackend.find_project_packages | 1000 | 0.369400 | 0.002800 | 131.93x |
| CachingFileBackend.get_by_relfn (first) | 1000 | 0.003000 | 0.000900 | 3.33x |
| CachingFileBackend.get_by_relfn (last) | 1000 | 0.020800 | 0.000400 | 52.00x |
| CachingFileBackend.get_by_relfn (missing) | 1000 | 0.019700 | 0.000300 | 65.67x |
| CachingFileBackend.get_all_packages (cold) | 5000 | 262.089700 | 279.283750 | 0.94x |
| CachingFileBackend.get_all_packages (warm) | 5000 | 0.034500 | 0.001200 | 28.75x |
| CachingFileBackend.find_project_packages | 5000 | 1.846700 | 0.004650 | 397.14x |
| CachingFileBackend.get_by_relfn (first) | 5000 | 0.003850 | 0.001600 | 2.41x |
| CachingFileBackend.get_by_relfn (last) | 5000 | 0.109350 | 0.000600 | 182.25x |
| CachingFileBackend.get_by_relfn (missing) | 5000 | 0.097900 | 0.000400 | 244.75x |
