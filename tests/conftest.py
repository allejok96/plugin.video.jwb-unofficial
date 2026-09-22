from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Dict, NamedTuple

import pytest

# pytest sets the python PATH to ./test
# so we must add ./test/.. to path to be able to import resources
# This is not the case for python -m pytest, but whatever
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import resources.lib.kodi
import resources.lib.jwlib.media as jwlib
from resources.lib.kodi.fake import FakeKodiInterface
from resources.lib.jwlib.media import Category, Media, Language, NotFoundError, BaseSession, File, Subtitle, const
from resources.lib.jwlib.media.const import CLIENT_FIRETV, CLIENT_NONE, CLIENT_APPLETV


@pytest.fixture(autouse=True)
def kodi(monkeypatch) -> FakeKodiInterface:
    """Monkeypatch the Kodi interface to a mock object, this is used on all tests"""

    fake = FakeKodiInterface()
    monkeypatch.setattr(resources.lib.kodi, 'instance', fake)
    return fake


class FakeSession(BaseSession):
    """jwlib mock session"""

    def __init__(self, language='E', hidden: bool = False):
        super().__init__(language=language, client_type=CLIENT_NONE if hidden else CLIENT_APPLETV)

        self.get_category_calls: list[tuple[str, bool]] = []
        self.get_media_calls: list[str] = []

        self.missing_categories: set[str] = set()
        self.languages: list[Language] = []
        self.media: dict[str, Media] = {}
        self.missing_media: set[str] = set()
        self.translations: dict[str, str] = {}

    def get_category(self, key=const.ROOT_CATEGORY, *, include_media=True) -> Category:
        self.get_category_calls.append((key, include_media))

        if key in self.missing_categories:
            raise NotFoundError
        else:
            return super().get_category(key, include_media=include_media)

    def get_languages(self) -> list[Language]:
        if not self.languages:
            raise NotImplementedError
        return self.languages

    def get_media(self, key: str) -> Media:
        self.get_media_calls.append(key)

        if key in self.missing_media:
            raise NotFoundError
        if not self.media:
            raise NotImplementedError
        return self.media[key]

    def get_translations(self) -> dict[str, str]:
        if not self.translations:
            raise NotImplementedError
        return self.translations

    def request_category_media(self, key: str, *, offset: int) -> tuple[list[Media], int]:
        raise NotImplementedError

    def request_category(self, key: str, *, include_media=True) -> Category:
        raise NotImplementedError

    def add_common_languages(self):
        self.languages = [
            Language(code='D', iso='de', name='German', vernacular='Deutsch'),
            Language(code='E', iso='en', name='English', vernacular='English'),
            Language(code='F', iso='fr', name='French', vernacular='Français'),
            Language(code='Z', iso='sv', name='Swedish', vernacular='Svenska'),
        ]


class SessionArgs(NamedTuple):
    language: str
    hidden: bool


class SessionStorage:
    def __init__(self):
        self._sessions: dict[SessionArgs, FakeSession] = {}
        self.invalid_languages: set[str] = set()

    def add(self, lang: str, *, hidden=False) -> FakeSession:
        session = FakeSession(language=lang, hidden=hidden)
        self._sessions[SessionArgs(lang, hidden)] = session
        return session

    def get(self, lang: str, *, hidden=False):
        if lang in self.invalid_languages:
            raise NotFoundError
        assert SessionArgs(lang, hidden) in self._sessions,\
            f'Trying to access session [{lang} hidden={hidden}] which has not been defined by the test'
        return self._sessions[SessionArgs(lang, hidden)]


@pytest.fixture(autouse=True)
def sessions(monkeypatch, kodi) -> SessionStorage:
    """Monkeypatch jwlib to return mock sessions

    This patches `get_session()` itself (rather than `jwapi._get_session()`), so real code such as
    `jwapi._get_session()`, `request_languages()` and `request_translations()` keeps running for real,
    it just ends up with a `FakeSession` at the bottom.

    `get_session()` is patched in two places because `jwapi` imported the name directly into its own
    namespace (`from resources.lib.jwlib.media import get_session`), so patching the original function
    in `jwlib.media` alone would not affect calls made from within `jwapi`.
    """

    storage = SessionStorage()

    def fake_get_session(language: str = 'E', client_type: str = CLIENT_FIRETV) -> BaseSession:
        return storage.get(lang=language, hidden=client_type == CLIENT_NONE)

    monkeypatch.setattr(jwlib, 'get_session', fake_get_session)

    return storage


@pytest.fixture
def session(sessions) -> FakeSession:
    """Shortcut to an English mock session"""
    return sessions.add('E')


@pytest.fixture
def languages() -> list[Language]:
    """Shortcut to a sample list of Language objects, see FakeSession.add_common_languages()"""
    dummy = FakeSession()
    dummy.add_common_languages()
    return dummy.languages
