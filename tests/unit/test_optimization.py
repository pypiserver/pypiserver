"""Tests for optimization enablers."""

import pytest

from pypiserver.optimization import (
    memoize,
)

from tests.unit.doubles import Spy


class TestMemoize:
    """Tests for memoization."""

    @pytest.mark.parametrize('args, kwargs, output', (
        (('a',), {}, 7),
        (('a',), {'b': 2}, 7),
        ((), {'b': 2}, 7),
        ((), {'b': 2}, {'foo': 'bar'}),
    ))
    def test_three_calls(self, args, kwargs, output):
        """Ensure we can call multiple times and only run once."""
        num_calls = 3
        memoized = memoize()(Spy(returns=output))
        assert memoized(*args, **kwargs) == output
        assert len(memoized.calls) == 1
        for _ in range(num_calls):
            assert memoized(*args, **kwargs) == output
            assert len(memoized.calls) == 1

    @pytest.mark.parametrize('args, kwargs', (
        (({1, 2},), {}),  # sets are unhashable
        ((1,), {'b': {1: 2}}),  # dicts are unhashable
    ))
    def test_unmemoizables(self, args, kwargs):
        """Ensure we throw errors appropriately for unmemoizable items."""
        memoized = memoize()(Spy(returns=7))
        with pytest.raises(TypeError):
            memoized(*args, **kwargs)

    def test_max_records(self):
        """Ensure old records are discarded when needed."""
        memoized = memoize(max_records=2)(Spy(returns=7))

        # Make two calls and watch the call count increase
        assert memoized(1) == 7
        assert memoized.calls.count == 1

        assert memoized(2) == 7
        assert memoized.calls.count == 2

        # Memoized calls now do not increase the call count
        assert memoized(1) == 7
        assert memoized.calls.count == 2

        assert memoized(2) == 7
        assert memoized.calls.count == 2

        # Make a new call, and see the call count increase
        assert memoized(3) == 7
        assert memoized.calls.count == 3

        # Our second-to-last call is still memoized
        assert memoized(2) == 7
        assert memoized.calls.count == 3

        # But our first call was dropped to make room for the newest
        assert memoized(1) == 7
        assert memoized.calls.count == 4
