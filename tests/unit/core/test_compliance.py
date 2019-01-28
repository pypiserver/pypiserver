"""Tests for the compliance module."""

import pytest

from pypiserver.core.compliance import Pep426, Pep503


class TestPep426:
    """Validate Pep426 compliance."""

    @pytest.mark.parametrize('name, exp', (
        ('foo', True),
        ('foo-bar', True),
        ('foo_bar', True),
        ('foo1_bar', True),
        ('1foo', True),
        ('1foo2', True),
        ('foo.bar_baz', True),
        ('_foo', False),
        ('foo_', False),
        ('_foo_', False),
        ('-foo', False),
        ('foo-', False),
        ('.foo', False),
        ('foo.', False),
        ('foo*bar', False),
        ('foo&bar', False),
        ('foo$bar', False),
        ('foo\nbar', False),
    ))
    def test_valid_name(self, name, exp):
        """Ensure we are correctly parsing name validity."""
        assert Pep426.valid_name(name) is exp


class TestPep503:
    """Validate Pep503 compliance."""

    @pytest.mark.parametrize('name, exp', (
        ('foo', 'foo'),
        ('FoO', 'foo'),
        ('--Foo', '-foo'),  # not a valid name, but normalizable
        ('fo--o', 'fo-o'),
        ('fo_o', 'fo-o'),
        ('fo__o.--o-', 'fo-o-o-'),
    ))
    def test_normalized(self, name, exp):
        """Ensure we normalize names as expected."""
        assert Pep503.normalized_name(name) == exp
