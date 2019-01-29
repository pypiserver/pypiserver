"""Async utilities for stores."""

import asyncio


class AsyncStore:
    """A base with some helpers for asynchronous stores."""

    def __init__(self):
        """Instantiate the mixin."""
        self._event_loop: asyncio.AbstractEventLoop = None

    @property
    def _loop(self) -> asyncio.AbstractEventLoop:
        """Return the running event loop."""
        if self._event_loop is None:
            self._event_loop = asyncio.get_running_loop()
        return self._event_loop
