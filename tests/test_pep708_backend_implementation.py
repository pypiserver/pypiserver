#!/usr/bin/env python3
"""
PEP 708 Backend Implementation Tests
Tests the actual PEP 708 implementation in backend.py
"""

import pytest
import tempfile
import os
import configparser
from unittest.mock import Mock, patch
from pathlib import Path

from pypiserver.backend import BackendProxy, SimpleFileBackend, CachingFileBackend
from pypiserver.config import Config


class TestBackendPEP708Implementation:
    """Test the actual PEP 708 implementation in backend classes."""
    
    def test_backend_proxy_pep708_metadata_loading(self):
        """Test BackendProxy loads PEP 708 metadata correctly."""
        config_content = """
[projects.test-package]
tracks = https://trusted-index.org/simple/test-package/
alternate-locations = https://alt-index.org/simple/test-package/,https://backup-index.org/simple/test-package/

[projects.another-package]
tracks = https://pypi.org/simple/another-package/
alternate-locations = 
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            # Create mock config
            mock_config = Mock()
            mock_config.pep708_config_path = config_path
            mock_config.hash_algo = 'sha256'
            mock_config.roots = ['/tmp']
            
            # Test BackendProxy
            backend = BackendProxy(SimpleFileBackend(mock_config))
            
            # Test metadata retrieval
            meta = backend.get_pep708_metadata('test-package')
            assert meta['tracks'] == ['https://trusted-index.org/simple/test-package/']
            assert len(meta['alternate-locations']) == 2
            assert 'https://alt-index.org/simple/test-package/' in meta['alternate-locations']
            assert 'https://backup-index.org/simple/test-package/' in meta['alternate-locations']
            
            # Test another package
            meta = backend.get_pep708_metadata('another-package')
            assert meta['tracks'] == ['https://pypi.org/simple/another-package/']
            assert meta['alternate-locations'] == []
            
            # Test non-existent project
            meta = backend.get_pep708_metadata('non-existent')
            assert meta == {"tracks": [], "alternate-locations": []}
            
        finally:
            os.unlink(config_path)
    
    def test_backend_proxy_no_config_path(self):
        """Test BackendProxy when no config path is provided."""
        mock_config = Mock()
        mock_config.pep708_config_path = None
        mock_config.hash_algo = 'sha256'
        mock_config.roots = ['/tmp']
        
        backend = BackendProxy(SimpleFileBackend(mock_config))
        meta = backend.get_pep708_metadata('any-package')
        assert meta == {"tracks": [], "alternate-locations": []}
    
    def test_backend_proxy_nonexistent_config_file(self):
        """Test BackendProxy when config file doesn't exist."""
        mock_config = Mock()
        mock_config.pep708_config_path = '/non/existent/path'
        mock_config.hash_algo = 'sha256'
        mock_config.roots = ['/tmp']
        
        backend = BackendProxy(SimpleFileBackend(mock_config))
        meta = backend.get_pep708_metadata('any-package')
        assert meta == {"tracks": [], "alternate-locations": []}
    
    def test_backend_proxy_invalid_config_file(self):
        """Test BackendProxy with invalid config file content."""
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
    
    def test_backend_proxy_malformed_sections(self):
        """Test BackendProxy with malformed section names."""
        config_content = """
[projects]
tracks = https://example.com/
[not-projects.valid]
tracks = https://example.com/
[projects.]
tracks = https://example.com/
[projects.valid-package]
tracks = https://example.com/simple/valid-package/
alternate-locations = https://alt.example.com/simple/valid-package/
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
            
            # Only valid-package should be loaded
            meta = backend.get_pep708_metadata('valid-package')
            assert meta['tracks'] == ['https://example.com/simple/valid-package/']
            assert meta['alternate-locations'] == ['https://alt.example.com/simple/valid-package/']
            
            # Other packages should return empty metadata
            meta = backend.get_pep708_metadata('any-other-package')
            assert meta == {"tracks": [], "alternate-locations": []}
            
        finally:
            os.unlink(config_path)
    
    def test_backend_proxy_whitespace_handling(self):
        """Test BackendProxy handles whitespace in config values correctly."""
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
    
    def test_backend_proxy_empty_values(self):
        """Test BackendProxy with empty values in config."""
        config_content = """
[projects.test-package]
tracks = 
alternate-locations = 
[projects.another-package]
tracks = https://trusted-index.org/simple/another-package/
alternate-locations = 
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
            
            # Test package with empty values
            meta = backend.get_pep708_metadata('test-package')
            assert meta['tracks'] == []
            assert meta['alternate-locations'] == []
            
            # Test package with tracks but empty alternate-locations
            meta = backend.get_pep708_metadata('another-package')
            assert meta['tracks'] == ['https://trusted-index.org/simple/another-package/']
            assert meta['alternate-locations'] == []
            
        finally:
            os.unlink(config_path)
    
    def test_backend_proxy_delegation(self):
        """Test BackendProxy properly delegates other methods to wrapped backend."""
        mock_config = Mock()
        mock_config.pep708_config_path = None
        mock_config.hash_algo = 'sha256'
        mock_config.roots = ['/tmp']
        
        mock_backend = Mock()
        mock_backend.get_all_packages.return_value = []
        mock_backend.find_project_packages.return_value = []
        mock_backend.find_version.return_value = []
        mock_backend.get_projects.return_value = []
        mock_backend.exists.return_value = False
        mock_backend.package_count.return_value = 0
        mock_backend.add_package.return_value = None
        mock_backend.remove_package.return_value = None
        mock_backend.digest.return_value = None
        
        backend = BackendProxy(mock_backend)
        
        # Test delegation
        backend.get_all_packages()
        mock_backend.get_all_packages.assert_called_once()
        
        backend.find_project_packages('test')
        mock_backend.find_project_packages.assert_called_once_with('test')
        
        backend.find_version('test', '1.0')
        mock_backend.find_version.assert_called_once_with('test', '1.0')
        
        backend.get_projects()
        mock_backend.get_projects.assert_called_once()
        
        backend.exists('test.tar.gz')
        mock_backend.exists.assert_called_once_with('test.tar.gz')
        
        backend.package_count()
        mock_backend.package_count.assert_called_once()
        
        backend.add_package('test.tar.gz', None)
        mock_backend.add_package.assert_called_once_with('test.tar.gz', None)
        
        backend.remove_package(None)
        mock_backend.remove_package.assert_called_once_with(None)
        
        backend.digest(None)
        mock_backend.digest.assert_called_once_with(None)


class TestBackendPEP708WithRealConfig:
    """Test PEP 708 with real configuration objects."""
    
    def test_backend_pep708_with_real_config(self):
        """Test BackendProxy with real Config object."""
        config_content = """
[projects.test-package]
tracks = https://trusted-index.org/simple/test-package/
alternate-locations = https://alt-index.org/simple/test-package/
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            # Create real config
            config = Config.from_args(['run', '--pep708-config', config_path, '/tmp'])
            
            # Create backend with real config
            backend = BackendProxy(SimpleFileBackend(config))
            
            # Test metadata retrieval
            meta = backend.get_pep708_metadata('test-package')
            assert meta['tracks'] == ['https://trusted-index.org/simple/test-package/']
            assert meta['alternate-locations'] == ['https://alt-index.org/simple/test-package/']
            
        finally:
            os.unlink(config_path)
    
    def test_caching_file_backend_pep708(self):
        """Test CachingFileBackend with PEP 708 metadata."""
        config_content = """
[projects.test-package]
tracks = https://trusted-index.org/simple/test-package/
alternate-locations = https://alt-index.org/simple/test-package/
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            # Create real config
            config = Config.from_args(['run', '--pep708-config', config_path, '/tmp'])
            
            # Create backend with real config
            backend = BackendProxy(CachingFileBackend(config))
            
            # Test metadata retrieval
            meta = backend.get_pep708_metadata('test-package')
            assert meta['tracks'] == ['https://trusted-index.org/simple/test-package/']
            assert meta['alternate-locations'] == ['https://alt-index.org/simple/test-package/']
            
        finally:
            os.unlink(config_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=pypiserver.backend', '--cov-report=term-missing'])
