"""
Wrapper for settings.xml
"""
import logging
from enum import Enum
from typing import List

import resources.lib.jwlib.media as jwlib

from resources.lib.kodi import kodi

logger = logging.getLogger(__name__)


def _get_search_translation(lang: str) -> str:
    try:
        return jwlib.get_session(lang).get_translations()['hdgSearch']
    except KeyError:
        logger.debug('Failed to find translation of "Search"')
    except Exception:
        logger.debug('Failed to fetch translated strings')
    return 'Search'


def update_search_translation(lang: str):
    """Get translation of the word "search" from jw.org - overkill but so cool"""

    kodi().set_setting('search_tr', _get_search_translation(lang))


class SubtitleMode(Enum):
    OFF = 0
    ON = 1
    ORIG_AND_FOREIGN = 2
    FOREIGN = 3


class Settings:
    @property
    def enable_fallback(self) -> bool:
        return kodi().get_setting_bool('enable_fallback')

    @enable_fallback.setter
    def enable_fallback(self, value: bool):
        kodi().set_setting_bool('enable_fallback', value)

    @property
    def fallback_language(self) -> str:
        return self.second_language if self.enable_fallback else self.language

    @property
    def first_run(self) -> bool:
        return kodi().get_setting_bool('startupmsg')

    @first_run.setter
    def first_run(self, value: bool):
        kodi().set_setting_bool('startupmsg', value)

    @property
    def language(self) -> str:
        return kodi().get_setting('language')

    @property
    def language_history(self) -> List[str]:
        return kodi().get_setting('lang_history').split()

    def _append_to_language_history(self, code):
        if code:
            history = [code] + [h for h in self.language_history if h != code]
            kodi().set_setting('lang_history', ' '.join(history[0:5]))

    @property
    def original_audio(self) -> bool:
        return kodi().get_setting_bool('original_audio')

    @original_audio.setter
    def original_audio(self, value: bool):
        kodi().set_setting_bool('original_audio', value)

    @property
    def original_audio_language(self) -> str:
        return self.second_language if self.original_audio else self.language

    @property
    def resolution(self) -> int:
        return int(kodi().get_setting('video_resolution'))

    @resolution.setter
    def resolution(self, value: int):
        kodi().set_setting('video_resolution', str(value))

    @property
    def search_label(self) -> str:
        return kodi().get_setting('search_tr')

    @property
    def second_language(self) -> str:
        return kodi().get_setting('second_language')

    @property
    def subtitle_mode(self) -> SubtitleMode:
        return SubtitleMode(int(kodi().get_setting('subtitle_mode')))

    @subtitle_mode.setter
    def subtitle_mode(self, mode: SubtitleMode):
        kodi().set_setting('subtitle_mode', str(mode.value))

    @property
    def tmp_language(self) -> str:
        return kodi().get_setting('lang_next')

    @tmp_language.setter
    def tmp_language(self, value: str):
        kodi().set_setting('lang_next', value)
        self._append_to_language_history(value)

    @property
    def token(self) -> str:
        return kodi().get_setting('jwt_token')

    @token.setter
    def token(self, value: str):
        kodi().set_setting('jwt_token', value)

    # The language setters are special since they require two arguments

    def set_language(self, code: str, name: str):
        kodi().set_setting('language', code)
        kodi().set_setting('lang_name', name)
        self._append_to_language_history(code)
        update_search_translation(code)

    def set_second_language(self, code: str, name: str):
        kodi().set_setting('second_language', code)
        kodi().set_setting('second_language_name', name)
        self._append_to_language_history(code)


settings = Settings()
