"""
Language list and info
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

from .._deprecated import deprecated

__all__ = (
    'Language',
)


@dataclass
class Language:
    """Information about a language"""

    code: str
    """JW language code.

    This is the code that can be passed to `get_session()`.
    """

    iso: str = ''
    """ISO 639 language code."""

    name: str = ''
    """Display name."""

    # This seems to always be False
    # @property
    # def pair(self) -> bool:
    #    return self.dict.get('isLangPair', False)

    rtl: bool = False
    """True if written right to left."""

    script: str = ''
    """Type of script, like ``ROMAN`` or ``CYRILLIC``."""

    signed: bool = False
    """True if it's a sign language."""

    vernacular: str = ''
    """Display name in the language itself."""

    @property
    @deprecated("Use `dataclasses.asdict()` instead.")
    def data(self) -> dict:
        return asdict(self)
