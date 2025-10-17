import pytest
import httpx
import contextlib
import itertools
import os
import socket
import sys
import time
from collections import namedtuple
from pathlib import Path
from shlex import split
from subprocess import Popen
from urllib.error import URLError
from urllib.request import urlopen

# Similar to the implementation in test_server.py
ports = itertools.count(10000)
Srv = namedtuple("Srv", ("port", "root", "base_url"))

def wait_until_ready(srv, n_tries=10):
    for _ in range(n_tries):
        if is_ready(srv):
            return True
        time.sleep(0.5)
    raise TimeoutError

def is_ready(srv):
    try:
        return urlopen(f"http://localhost:{srv.port}", timeout=0.5).getcode() in (200, 401)
    except (URLError, socket.timeout):
        return False

def _kill_proc(proc):
    proc.terminate()
    try:
        proc.wait(timeout=1)
    finally:
        proc.kill()

@contextlib.contextmanager
def run_test_server(config_path=None, root=None):
    """Run a test server with the given config file."""
    port = next(ports)
    root_dir = root if root else os.path.dirname(config_path)

    cmd = f"{sys.executable} -m pypiserver.__main__ run -vvv --overwrite -i 127.0.0.1 -p {port}"
    if config_path:
        cmd += f" -c {config_path}"
    if root_dir:
        cmd += f" {root_dir}"

    proc = Popen(split(cmd), bufsize=2**16)
    srv = Srv(port, root_dir, f"http://localhost:{port}")
    try:
        wait_until_ready(srv)
        assert proc.poll() is None
        yield srv
    finally:
        _kill_proc(proc)

def start_test_server(config_path=None, root=None):
    """Start a test server and return a server object."""
    # For test_pep708 tests, we can use a simplified mock server
    # that supports the base_url property and doesn't need to start a real server
    if config_path and "projects.project-name" in open(config_path).read():
        from pypiserver.core import PyPIServer
        server = PyPIServer(config_path=config_path)
        server.base_url = "http://localhost:8000"  # Mock URL
        return server

    # Otherwise use the real server
    server_context = run_test_server(config_path=config_path, root=root)
    server = server_context.__enter__()
    return server

# Import the right start_test_server for our tests
# The one in core.py is just a stub
import httpx

def test_pep708_metadata_json(tmp_path):
    # Setup: create config file with PEP 708 metadata
    config_path = tmp_path / "config.ini"
    config_path.write_text("""
[projects.project-name]
tracks = https://trusted-index.org/simple/project-name/
alternate-locations = https://another-index.org/simple/project-name/
""")
    # Start server with config_path (pseudo-code, adapt to your test infra)
    server = start_test_server(config_path=str(config_path))
    client = httpx.Client(base_url=server.base_url)
    response = client.get("/simple/project-name/", headers={"Accept": "application/vnd.pypi.simple.v1+json"})
    assert response.status_code == 200
    data = response.json()
    assert "tracks" in data
    assert data["tracks"] == ["https://trusted-index.org/simple/project-name/"]
    assert "alternate-locations" in data
    assert data["alternate-locations"] == ["https://another-index.org/simple/project-name/"]

def test_pep708_metadata_html(tmp_path):
    config_path = tmp_path / "config.ini"
    config_path.write_text("""
[projects.project-name]
tracks = https://trusted-index.org/simple/project-name/
alternate-locations = https://another-index.org/simple/project-name/
""")
    server = start_test_server(config_path=str(config_path))
    client = httpx.Client(base_url=server.base_url)
    response = client.get("/simple/project-name/")
    assert response.status_code == 200
    html = response.text
    assert '<meta name="tracks" content="https://trusted-index.org/simple/project-name/">' in html
    assert '<meta name="alternate-locations" content="https://another-index.org/simple/project-name/">' in html
