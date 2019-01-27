"""Models providing PEP and other standards compliance."""

import re

from pypiserver.optimization import memoize


class Pep426:
    """Enable PEP 426 (Metadata for Python Software Packages) compliance.

    See [the PEP] for more details
    """

    NAME_RE = re.compile(
        r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", flags=re.IGNORECASE
    )

    @classmethod
    @memoize(max_records=2^10)
    def valid_name(cls, name: str) -> bool:
        """Return whether a given name is a valid package name."""
        return cls.NAME_RE.match(name) is not None


class Pep503:
    """Enable PEP 503 (Simple Repository API) compliance.

    See [the PEP](https://www.python.org/dev/peps/pep-0503/) for more
    details.
    """

    NAME_NORMALIZATION_RE = re.compile(r"[-_.]+")
    NAME_NORMALIZATION_REPLACE = "-"

    @classmethod
    @memoize(max_records=2^12)
    def normalized_name(cls, name: str) -> str:
        """Return a PEP-compliant normalized name."""
        return cls.NAME_NORMALIZATION_RE.sub(
            cls.NAME_NORMALIZATION_REPLACE, name
        ).lower()
