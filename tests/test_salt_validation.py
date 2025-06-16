#!/usr/bin/env python

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pypiserver.config import Config

class TestHtpasswdValidation(unittest.TestCase):
    def setUp(self):
        # Create a temporary htpasswd file
        self.htpasswd_fd, self.htpasswd_file = tempfile.mkstemp()
        # Write a valid and an invalid entry
        with open(self.htpasswd_file, 'w') as f:
            f.write("valid:$apr1$salt$hashedpassword\n")
            f.write("invalid:$apr1$@salt$hashedpassword\n") # @ is not valid in salt

    def tearDown(self):
        # Clean up the temp file
        os.close(self.htpasswd_fd)
        os.unlink(self.htpasswd_file)

    @patch('pypiserver.config.HtpasswdFile')
    def test_safe_password_check(self, mock_htpasswd):
        # Set up the mock
        mock_file = MagicMock()
        mock_htpasswd.return_value = mock_file

        # Make check_password raise ValueError for the invalid user
        def mock_check_password(username, password):
            if username == 'invalid':
                raise ValueError("invalid characters in apr_md5_crypt salt")
            return username == 'valid' and password == 'correct'

        mock_file.check_password.side_effect = mock_check_password

        # Configure the auth function
        config = Config()
        config.password_file = self.htpasswd_file
        config.authenticate = ['update']

        # Get the auther function
        auther = config.get_auther(None)

        # Test with valid user
        self.assertTrue(auther('valid', 'correct'))
        self.assertFalse(auther('valid', 'wrong'))

        # Test with invalid user (should return False instead of raising ValueError)
        with self.assertLogs(level='ERROR') as cm:
            result = auther('invalid', 'anypassword')
            self.assertFalse(result)
            self.assertIn("Authentication failed: Invalid characters in password hash", cm.output[0])

if __name__ == '__main__':
    unittest.main()
