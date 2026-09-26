"""
Wrapper for website language API
"""
from __future__ import annotations

from .._dictwrapper import _DictWrapper
from .._request import get_json as _get_json

_LANGUAGE_API = 'https://www.jw.org/en/languages'

class Language(_DictWrapper):

    def __repr__(self):
        try:
            return f'<{self.__class__.__name__} {self.code!r}>'
        except Exception:
            return super().__repr__()

    @property
    def code(self) -> str:
        """JW language code"""
        return self.data['langcode']

    @property
    def isocode(self) -> str:
        """ISO 639 language code"""
        return self.data['symbol']

    @property
    def name(self) -> str:
        """Display name"""
        return self._get_string('name', '')

    @property
    def names(self) -> list[str]:
        """List of alternative names"""
        return self.data.get('altSpellings', [])

    @property
    def rtl(self) -> bool:
        """Right to left"""
        return self.data.get('direction') == 'rtl'

    @property
    def script(self) -> str:
        """Example: ROMAN"""
        return self.data['script']

    @property
    def signed(self) -> bool:
        """Sign language"""
        return self.data['isSignLanguage']

    @property
    def vernacular(self) -> str:
        """Display name in the language itself"""
        return self.data['vernacularName']


def get_languages() -> list[Language]:
    """Return list of available Languages"""
    return [Language(L) for L in _get_json(_LANGUAGE_API)['languages']]
