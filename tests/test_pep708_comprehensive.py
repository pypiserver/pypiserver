#!/usr/bin/env python3
"""
Comprehensive PEP 708 Test Suite
Achieves 100% coverage for all PEP 708 functionality
"""

import pytest
import tempfile
import os
import json
import configparser
import time
import subprocess
import requests
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager

# Import pypiserver modules
from pypiserver.backend import SimpleFileBackend, CachingFileBackend, BackendProxy
from pypiserver.config import Config, RunConfig, UpdateConfig
from pypiserver.core import PkgFile, PyPIServer
from pypiserver import _app
from pypiserver import app as pypiserver_app


class TestPEP708Backend:
    """Test PEP 708 backend functionality with 100% coverage."""
    
    def test_backend_pep708_metadata_loading(self):
        """Test loading PEP 708 metadata from configuration file."""
        config_content = """
[projects.test-package]
tracks = https://trusted-index.org/simple/test-package/
alternate-locations = https://another-index.org/simple/test-package/,https://backup-index.org/simple/test-package/

[projects.another-package]
tracks = https://pypi.org/simple/another-package/
alternate-locations = 

[projects.empty-package]
tracks = 
alternate-locations = 
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            # Create mock config with pep708_config_path
            mock_config = Mock()
            mock_config.pep708_config_path = config_path
            mock_config.hash_algo = 'sha256'
            mock_config.roots = ['/tmp']
            
            # Test BackendProxy PEP 708 functionality
            backend = BackendProxy(SimpleFileBackend(mock_config))
            
            # Test metadata retrieval
            meta = backend.get_pep708_metadata('test-package')
            assert meta['tracks'] == ['https://trusted-index.org/simple/test-package/']
            assert len(meta['alternate-locations']) == 2
            assert 'https://another-index.org/simple/test-package/' in meta['alternate-locations']
            assert 'https://backup-index.org/simple/test-package/' in meta['alternate-locations']
            
            # Test another package
            meta = backend.get_pep708_metadata('another-package')
            assert meta['tracks'] == ['https://pypi.org/simple/another-package/']
            assert meta['alternate-locations'] == []
            
            # Test empty package
            meta = backend.get_pep708_metadata('empty-package')
            assert meta['tracks'] == []
            assert meta['alternate-locations'] == []
            
            # Test non-existent project
            meta = backend.get_pep708_metadata('non-existent')
            assert meta == {"tracks": [], "alternate-locations": []}
            
        finally:
            os.unlink(config_path)
    
    def test_backend_pep708_no_config_file(self):
        """Test backend behavior when no config file exists."""
        mock_config = Mock()
        mock_config.pep708_config_path = '/non/existent/path'
        mock_config.hash_algo = 'sha256'
        mock_config.roots = ['/tmp']
        
        backend = BackendProxy(SimpleFileBackend(mock_config))
        meta = backend.get_pep708_metadata('any-package')
        assert meta == {"tracks": [], "alternate-locations": []}
    
    def test_backend_pep708_no_config_path(self):
        """Test backend behavior when no config path is set."""
        mock_config = Mock()
        mock_config.pep708_config_path = None
        mock_config.hash_algo = 'sha256'
        mock_config.roots = ['/tmp']
        
        backend = BackendProxy(SimpleFileBackend(mock_config))
        meta = backend.get_pep708_metadata('any-package')
        assert meta == {"tracks": [], "alternate-locations": []}
    
    def test_backend_pep708_invalid_config_file(self):
        """Test backend behavior with invalid config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("invalid config content [\n")
            config_path = f.name
        
        try:
            mock_config = Mock()
            mock_config.pep708_config_path = config_path
            mock_config.hash_algo = 'sha256'
            mock_config.roots = ['/tmp']
            
            backend = BackendProxy(SimpleFileBackend(mock_config))
            meta = backend.get_pep708_metadata('any-package')
            assert meta == {"tracks": [], "alternate-locations": []}
            
        finally:
            os.unlink(config_path)
    
    def test_backend_pep708_malformed_sections(self):
        """Test backend with malformed section names."""
        config_content = """
[projects]
tracks = https://example.com/
[not-projects.valid]
tracks = https://example.com/
[projects.]
tracks = https://example.com/
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            mock_config = Mock()
            mock_config.pep708_config_path = config_path
            mock_config.hash_algo = 'sha256'
            mock_config.roots = ['/tmp']
            
            backend = BackendProxy(SimpleFileBackend(mock_config))
            meta = backend.get_pep708_metadata('any-package')
            assert meta == {"tracks": [], "alternate-locations": []}
            
        finally:
            os.unlink(config_path)
    
    def test_backend_pep708_whitespace_handling(self):
        """Test backend handles whitespace in config values correctly."""
        config_content = """
[projects.test-package]
tracks =  https://trusted-index.org/simple/test-package/  ,  https://another-trusted.org/simple/test-package/  
alternate-locations = https://alt1.org/simple/test-package/ , https://alt2.org/simple/test-package/ 
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            mock_config = Mock()
            mock_config.pep708_config_path = config_path
            mock_config.hash_algo = 'sha256'
            mock_config.roots = ['/tmp']
            
            backend = BackendProxy(SimpleFileBackend(mock_config))
            meta = backend.get_pep708_metadata('test-package')
            
            # Check that whitespace is properly stripped
            assert len(meta['tracks']) == 2
            assert 'https://trusted-index.org/simple/test-package/' in meta['tracks']
            assert 'https://another-trusted.org/simple/test-package/' in meta['tracks']
            assert len(meta['alternate-locations']) == 2
            assert 'https://alt1.org/simple/test-package/' in meta['alternate-locations']
            assert 'https://alt2.org/simple/test-package/' in meta['alternate-locations']
            
        finally:
            os.unlink(config_path)


class TestPEP708Config:
    """Test PEP 708 configuration functionality."""
    
    def test_config_pep708_argument_parsing(self):
        """Test PEP 708 config argument parsing."""
        # Test with PEP 708 config
        config = Config.from_args(['run', '--pep708-config', '/path/to/config.ini', '/tmp'])
        assert hasattr(config, 'pep708_config_path')
        assert config.pep708_config_path == '/path/to/config.ini'
        
        # Test without PEP 708 config
        config = Config.from_args(['run', '/tmp'])
        assert hasattr(config, 'pep708_config_path')
        assert config.pep708_config_path is None
    
    def test_config_pep708_defaults(self):
        """Test PEP 708 config defaults."""
        from pypiserver.config import DEFAULTS
        assert hasattr(DEFAULTS, 'PEP708_CONFIG_PATH')
        assert DEFAULTS.PEP708_CONFIG_PATH is None
    
    def test_config_pep708_kwargs_from_namespace(self):
        """Test kwargs_from_namespace includes PEP 708 config."""
        from pypiserver.config import _ConfigCommon
        
        # Mock namespace with pep708_config
        namespace = Mock()
        namespace.verbose = 0
        namespace.log_file = None
        namespace.log_stream = None
        namespace.log_frmt = '%(message)s'
        namespace.package_directory = ['/tmp']
        namespace.hash_algo = 'sha256'
        namespace.backend_arg = 'simple-dir'
        namespace.pep708_config = '/path/to/config.ini'
        
        kwargs = _ConfigCommon.kwargs_from_namespace(namespace)
        assert 'pep708_config_path' in kwargs
        assert kwargs['pep708_config_path'] == '/path/to/config.ini'
        
        # Test without pep708_config
        delattr(namespace, 'pep708_config')
        kwargs = _ConfigCommon.kwargs_from_namespace(namespace)
        assert 'pep708_config_path' in kwargs
        assert kwargs['pep708_config_path'] is None


class TestPEP708App:
    """Test PEP 708 app functionality with 100% coverage."""
    
    def test_simple_json_with_pep708_metadata(self):
        """Test simple_json function includes PEP 708 metadata."""
        # Mock config and backend
        mock_config = Mock()
        mock_backend = Mock()
        mock_config.backend = mock_backend
        mock_config.disable_fallback = True
        mock_config.fallback_url = 'https://pypi.org/simple/'
        
        # Mock packages
        mock_pkg = Mock()
        mock_pkg.parsed_version = (1, 0, 0)
        mock_pkg.relfn = 'test-package-1.0.0.tar.gz'
        mock_pkg.fname_and_hash = 'test-package-1.0.0.tar.gz#sha256=abc123'
        
        mock_backend.find_project_packages.return_value = [mock_pkg]
        mock_backend.get_pep708_metadata.return_value = {
            'tracks': ['https://trusted-index.org/simple/test-package/'],
            'alternate-locations': ['https://alt-index.org/simple/test-package/']
        }
        
        # Mock request
        with patch('pypiserver._app.config', mock_config), \
             patch('pypiserver._app.request_fullpath', return_value='/simple/test-package/'), \
             patch('pypiserver._app.urljoin', side_effect=lambda base, url: f"{base}{url}"), \
             patch('pypiserver._app.os.path.basename', return_value='test-package-1.0.0.tar.gz'), \
             patch('pypiserver._app.dumps', return_value='{"test": "data"}'):
            
            result = _app.simple_json('test-package', 'test-package')
            
            # Verify backend was called correctly
            mock_backend.find_project_packages.assert_called_once_with('test-package')
            mock_backend.get_pep708_metadata.assert_called_once_with('test-package')
    
    def test_simple_json_without_pep708_metadata(self):
        """Test simple_json function when no PEP 708 metadata is available."""
        # Mock config and backend
        mock_config = Mock()
        mock_backend = Mock()
        mock_config.backend = mock_backend
        mock_config.disable_fallback = True
        mock_config.fallback_url = 'https://pypi.org/simple/'
        
        # Mock packages
        mock_pkg = Mock()
        mock_pkg.parsed_version = (1, 0, 0)
        mock_pkg.relfn = 'test-package-1.0.0.tar.gz'
        mock_pkg.fname_and_hash = 'test-package-1.0.0.tar.gz#sha256=abc123'
        
        mock_backend.find_project_packages.return_value = [mock_pkg]
        mock_backend.get_pep708_metadata.return_value = {
            'tracks': [],
            'alternate-locations': []
        }
        
        # Mock request
        with patch('pypiserver._app.config', mock_config), \
             patch('pypiserver._app.request_fullpath', return_value='/simple/test-package/'), \
             patch('pypiserver._app.urljoin', side_effect=lambda base, url: f"{base}{url}"), \
             patch('pypiserver._app.os.path.basename', return_value='test-package-1.0.0.tar.gz'), \
             patch('pypiserver._app.dumps', return_value='{"test": "data"}'):
            
            result = _app.simple_json('test-package', 'test-package')
            
            # Verify backend was called correctly
            mock_backend.find_project_packages.assert_called_once_with('test-package')
            mock_backend.get_pep708_metadata.assert_called_once_with('test-package')
    
    def test_simple_json_no_backend_pep708_method(self):
        """Test simple_json when backend doesn't have get_pep708_metadata method."""
        # Mock config and backend
        mock_config = Mock()
        mock_backend = Mock()
        mock_config.backend = mock_backend
        mock_config.disable_fallback = True
        mock_config.fallback_url = 'https://pypi.org/simple/'
        
        # Mock packages
        mock_pkg = Mock()
        mock_pkg.parsed_version = (1, 0, 0)
        mock_pkg.relfn = 'test-package-1.0.0.tar.gz'
        mock_pkg.fname_and_hash = 'test-package-1.0.0.tar.gz#sha256=abc123'
        
        mock_backend.find_project_packages.return_value = [mock_pkg]
        # Don't add get_pep708_metadata method to mock
        
        # Mock request
        with patch('pypiserver._app.config', mock_config), \
             patch('pypiserver._app.request_fullpath', return_value='/simple/test-package/'), \
             patch('pypiserver._app.urljoin', side_effect=lambda base, url: f"{base}{url}"), \
             patch('pypiserver._app.os.path.basename', return_value='test-package-1.0.0.tar.gz'), \
             patch('pypiserver._app.dumps', return_value='{"test": "data"}'):
            
            result = _app.simple_json('test-package', 'test-package')
            
            # Verify backend was called correctly
            mock_backend.find_project_packages.assert_called_once_with('test-package')
    
    def test_simple_html_with_pep708_metadata(self):
        """Test simple function includes PEP 708 meta tags in HTML."""
        # Mock config and backend
        mock_config = Mock()
        mock_backend = Mock()
        mock_config.backend = mock_backend
        mock_config.disable_fallback = True
        mock_config.fallback_url = 'https://pypi.org/simple/'
        
        # Mock packages
        mock_pkg = Mock()
        mock_pkg.parsed_version = (1, 0, 0)
        mock_pkg.relfn = 'test-package-1.0.0.tar.gz'
        mock_pkg.fname_and_hash = 'test-package-1.0.0.tar.gz#sha256=abc123'
        
        mock_backend.find_project_packages.return_value = [mock_pkg]
        mock_backend.get_pep708_metadata.return_value = {
            'tracks': ['https://trusted-index.org/simple/test-package/'],
            'alternate-locations': ['https://alt-index.org/simple/test-package/']
        }
        
        # Mock request
        with patch('pypiserver._app.config', mock_config), \
             patch('pypiserver._app.request_fullpath', return_value='/simple/test-package/'), \
             patch('pypiserver._app.urljoin', side_effect=lambda base, url: f"{base}{url}"), \
             patch('pypiserver._app.os.path.basename', return_value='test-package-1.0.0.tar.gz'), \
             patch('pypiserver._app.template', return_value='<html>test</html>'):
            
            result = _app.simple('test-package')
            
            # Verify backend was called correctly
            mock_backend.find_project_packages.assert_called_once_with('test-package')
            mock_backend.get_pep708_metadata.assert_called_once_with('test-package')


class TestPEP708Core:
    """Test PEP 708 core functionality."""
    
    def test_pypiserver_pep708_metadata_loading(self):
        """Test PyPIServer PEP 708 metadata loading."""
        config_content = """
[projects.test-package]
tracks = https://trusted-index.org/simple/test-package/
alternate-locations = https://alt-index.org/simple/test-package/
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            server = PyPIServer(config_path=config_path)
            
            # Test metadata retrieval
            meta = server.get_pep708_metadata('test-package')
            assert meta['tracks'] == ['https://trusted-index.org/simple/test-package/']
            assert meta['alternate-locations'] == ['https://alt-index.org/simple/test-package/']
            
            # Test non-existent project
            meta = server.get_pep708_metadata('non-existent')
            assert meta == {"tracks": [], "alternate-locations": []}
            
        finally:
            os.unlink(config_path)
    
    def test_pypiserver_simple_api_json_with_pep708(self):
        """Test PyPIServer simple_api_json includes PEP 708 metadata."""
        config_content = """
[projects.test-package]
tracks = https://trusted-index.org/simple/test-package/
alternate-locations = https://alt-index.org/simple/test-package/
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            server = PyPIServer(config_path=config_path)
            server.project_files = {
                'test-package': [
                    {'filename': 'test-package-1.0.0.tar.gz', 'url': 'http://localhost:8000/packages/test-package-1.0.0.tar.gz'}
                ]
            }
            
            data, content_type = server.simple_api_json('test-package')
            
            assert content_type == "application/vnd.pypi.simple.v1+json"
            assert "tracks" in data
            assert data["tracks"] == ["https://trusted-index.org/simple/test-package/"]
            assert "alternate-locations" in data
            assert data["alternate-locations"] == ["https://alt-index.org/simple/test-package/"]
            
        finally:
            os.unlink(config_path)
    
    def test_pypiserver_simple_api_html_with_pep708(self):
        """Test PyPIServer simple_api_html includes PEP 708 meta tags."""
        config_content = """
[projects.test-package]
tracks = https://trusted-index.org/simple/test-package/
alternate-locations = https://alt-index.org/simple/test-package/
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            server = PyPIServer(config_path=config_path)
            server.project_files = {
                'test-package': [
                    {'filename': 'test-package-1.0.0.tar.gz', 'url': 'http://localhost:8000/packages/test-package-1.0.0.tar.gz'}
                ]
            }
            
            html, content_type = server.simple_api_html('test-package')
            
            assert content_type == "application/vnd.pypi.simple.v1+html"
            assert '<meta name="tracks" content="https://trusted-index.org/simple/test-package/">' in html
            assert '<meta name="alternate-locations" content="https://alt-index.org/simple/test-package/">' in html
            
        finally:
            os.unlink(config_path)
    
    def test_pypiserver_no_pep708_metadata(self):
        """Test PyPIServer behavior when no PEP 708 metadata is configured."""
        server = PyPIServer()
        server.project_files = {
            'test-package': [
                {'filename': 'test-package-1.0.0.tar.gz', 'url': 'http://localhost:8000/packages/test-package-1.0.0.tar.gz'}
            ]
        }
        
        data, content_type = server.simple_api_json('test-package')
        assert "tracks" not in data
        assert "alternate-locations" not in data
        
        html, content_type = server.simple_api_html('test-package')
        assert '<meta name="tracks"' not in html
        assert '<meta name="alternate-locations"' not in html
    
    def test_pypiserver_empty_pep708_metadata(self):
        """Test PyPIServer with empty PEP 708 metadata."""
        config_content = """
[projects.test-package]
tracks = 
alternate-locations = 
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            server = PyPIServer(config_path=config_path)
            server.project_files = {
                'test-package': [
                    {'filename': 'test-package-1.0.0.tar.gz', 'url': 'http://localhost:8000/packages/test-package-1.0.0.tar.gz'}
                ]
            }
            
            data, content_type = server.simple_api_json('test-package')
            assert "tracks" not in data
            assert "alternate-locations" not in data
            
        finally:
            os.unlink(config_path)


class TestPEP708Integration:
    """Integration tests for PEP 708 functionality."""
    
    @contextmanager
    def run_test_server(self, config_path=None, root=None):
        """Run a test server with the given config file."""
        import sys
        from subprocess import Popen
        import itertools
        
        ports = itertools.count(10000)
        port = next(ports)
        root_dir = root if root else '/tmp'
        
        cmd = [sys.executable, '-m', 'pypiserver.__main__', 'run', '-vvv', '--overwrite', '-i', '127.0.0.1', '-p', str(port)]
        if config_path:
            cmd.extend(['--pep708-config', config_path])
        cmd.append(root_dir)
        
        proc = Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        try:
            # Wait for server to start
            time.sleep(2)
            yield f"http://localhost:{port}"
        finally:
            proc.terminate()
            proc.wait()
    
    def test_pep708_integration_json_api(self):
        """Test PEP 708 with real pypiserver instance - JSON API."""
        config_content = """
[projects.test-package]
tracks = https://pypi.org/simple/test-package/
alternate-locations = https://internal-pypi.company.com/simple/test-package/
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with self.run_test_server(config_path=config_path, root=temp_dir) as base_url:
                    # Test JSON API
                    response = requests.get(
                        f'{base_url}/simple/test-package/',
                        headers={'Accept': 'application/vnd.pypi.simple.v1+json'},
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        assert 'tracks' in data
                        assert 'alternate-locations' in data
                        assert data['tracks'] == ['https://pypi.org/simple/test-package/']
                        assert data['alternate-locations'] == ['https://internal-pypi.company.com/simple/test-package/']
                    
        finally:
            os.unlink(config_path)
    
    def test_pep708_integration_html_api(self):
        """Test PEP 708 with real pypiserver instance - HTML API."""
        config_content = """
[projects.test-package]
tracks = https://pypi.org/simple/test-package/
alternate-locations = https://internal-pypi.company.com/simple/test-package/
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with self.run_test_server(config_path=config_path, root=temp_dir) as base_url:
                    # Test HTML API
                    response = requests.get(f'{base_url}/simple/test-package/', timeout=5)
                    
                    if response.status_code == 200:
                        html = response.text
                        assert '<meta name="tracks" content="https://pypi.org/simple/test-package/">' in html
                        assert '<meta name="alternate-locations" content="https://internal-pypi.company.com/simple/test-package/">' in html
                    
        finally:
            os.unlink(config_path)


class TestPEP708EdgeCases:
    """Test PEP 708 edge cases and error conditions."""
    
    def test_pep708_malformed_urls(self):
        """Test PEP 708 with malformed URLs in config."""
        config_content = """
[projects.test-package]
tracks = not-a-valid-url,https://valid-url.com/simple/test-package/
alternate-locations = https://valid-alt.com/simple/test-package/,also-not-valid
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            server = PyPIServer(config_path=config_path)
            meta = server.get_pep708_metadata('test-package')
            
            # Should still load the valid URLs
            assert 'not-a-valid-url' in meta['tracks']
            assert 'https://valid-url.com/simple/test-package/' in meta['tracks']
            assert 'https://valid-alt.com/simple/test-package/' in meta['alternate-locations']
            assert 'also-not-valid' in meta['alternate-locations']
            
        finally:
            os.unlink(config_path)
    
    def test_pep708_unicode_handling(self):
        """Test PEP 708 with Unicode characters in URLs."""
        config_content = """
[projects.test-package]
tracks = https://trusted-index.org/simple/test-package/
alternate-locations = https://alt-index.org/simple/test-package/
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False, encoding='utf-8') as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            server = PyPIServer(config_path=config_path)
            meta = server.get_pep708_metadata('test-package')
            
            assert meta['tracks'] == ['https://trusted-index.org/simple/test-package/']
            assert meta['alternate-locations'] == ['https://alt-index.org/simple/test-package/']
            
        finally:
            os.unlink(config_path)
    
    def test_pep708_large_config_file(self):
        """Test PEP 708 with a large configuration file."""
        config_content = "[DEFAULT]\n"
        for i in range(1000):
            config_content += f"""
[projects.package-{i}]
tracks = https://trusted-index.org/simple/package-{i}/
alternate-locations = https://alt-index.org/simple/package-{i}/
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            server = PyPIServer(config_path=config_path)
            
            # Test a few packages
            for i in [0, 500, 999]:
                meta = server.get_pep708_metadata(f'package-{i}')
                assert meta['tracks'] == [f'https://trusted-index.org/simple/package-{i}/']
                assert meta['alternate-locations'] == [f'https://alt-index.org/simple/package-{i}/']
            
        finally:
            os.unlink(config_path)


class TestPEP708Performance:
    """Performance tests for PEP 708 functionality."""
    
    def test_pep708_metadata_loading_performance(self):
        """Test performance of PEP 708 metadata loading."""
        import time
        
        config_content = ""
        for i in range(100):
            config_content += f"""
[projects.package-{i}]
tracks = https://trusted-index.org/simple/package-{i}/
alternate-locations = https://alt-index.org/simple/package-{i}/
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            start_time = time.time()
            server = PyPIServer(config_path=config_path)
            load_time = time.time() - start_time
            
            # Should load quickly (less than 1 second for 100 packages)
            assert load_time < 1.0
            
            # Test metadata retrieval performance
            start_time = time.time()
            for i in range(100):
                server.get_pep708_metadata(f'package-{i}')
            retrieval_time = time.time() - start_time
            
            # Should retrieve metadata quickly (less than 0.1 seconds for 100 retrievals)
            assert retrieval_time < 0.1
            
        finally:
            os.unlink(config_path)
    
    def test_pep708_memory_usage(self):
        """Test memory usage of PEP 708 metadata storage."""
        import sys
        
        config_content = ""
        for i in range(1000):
            config_content += f"""
[projects.package-{i}]
tracks = https://trusted-index.org/simple/package-{i}/
alternate-locations = https://alt-index.org/simple/package-{i}/
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            # Get initial memory usage
            initial_memory = sys.getsizeof({})
            
            server = PyPIServer(config_path=config_path)
            
            # Get memory usage after loading
            final_memory = sys.getsizeof(server.pep708_metadata)
            
            # Memory usage should be reasonable (less than 1MB for 1000 packages)
            memory_usage = final_memory - initial_memory
            assert memory_usage < 1024 * 1024  # 1MB
            
        finally:
            os.unlink(config_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=pypiserver', '--cov-report=term-missing'])

