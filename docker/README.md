<!-- -*-GFM-*- -->

# Docker Resources and Tests

This directory contains resources and tests for the docker image.

Note that for these tests to run, the pytest process must be able to run
`docker`. If you are on a system where that requires `sudo`, you will need to
run the tests with `sudo`.

Tests are here rather than in `/tests` because there's no reason to run these
tests as part of the usual `tox` process, which is run in CI against every
supported Python version. We only need to run the Docker tests once.

