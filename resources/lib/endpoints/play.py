import logging
import time
from typing import List, Dict, Set

from resources.lib.jwlib.media import NotFoundError, Media
from resources.lib.jwlib.media.const import MEDIA_VIDEO

from resources.lib.requests import PlayRequest
from resources.lib.jwgui import create_media_item
from resources.lib.jwapi import get_media, get_best_url
from resources.lib.kodi import kodi
from resources.lib.settings import settings, SubtitleMode

logger = logging.getLogger(__name__)


class _MultiLangMediaCache:
    """This abomination is so I can lazily call get() for multiple languages
    in play_media without having to figure out how to do that efficiently"""

    def __init__(self, key: str, hidden: bool):
        self.key = key
        self.hidden = hidden
        self.found: Dict[str, Media] = {}
        self.failed: Set[str] = set()

    def get(self, languages: List[str]) -> Media:
        for language in languages:
            if language in self.failed:
                continue
            if language in self.found:
                return self.found[language]
            try:
                media = get_media(self.key, languages=[language], hidden=self.hidden)
                self.found[language] = media
                return media
            except NotFoundError:
                logger.debug(f'Media not found: {language}/{self.key}')
                self.failed.add(language)

        raise NotFoundError


def _get_title_language(request_lang: str):
    if request_lang:
        return [request_lang]
    else:
        return [settings.language, settings.fallback_language]


def _get_playback_language(request_lang: str, is_video: bool):
    if request_lang:
        return [request_lang]
    elif is_video:
        return [settings.original_audio_language, settings.language, settings.fallback_language]
    else:
        return [settings.language, settings.fallback_language]


def _get_subtitle_visibility(lang: str):
    """Return True if subtitles should be displayed for the given language"""
    ss = settings.subtitle_mode

    if ss == SubtitleMode.ON:
        return True

    elif ss == SubtitleMode.ORIG_AND_FOREIGN:
        return lang != settings.language

    elif ss == SubtitleMode.FOREIGN:
        return lang not in (settings.language, settings.original_audio_language)

    else:  # SubtitleMode.OFF
        return False


def _set_subtitle_visibility(visible: bool):
    # Turn on/off subtitles without changing the global Kodi setting
    # TODO check if it can be set in ListItem in the future
    for i in range(20):
        if kodi().get_subtitles():
            kodi().show_subtitles(visible)
            break
        time.sleep(1)


def _get_subtitles(cached: _MultiLangMediaCache) -> List[str]:
    try:
        subtitle = cached.get([settings.language]).subtitle_url
        if subtitle:
            return [subtitle]
        logger.debug(f'No subtitles found for media {cached.key!r}')
    except NotFoundError:
        logger.debug(f'No subtitles found for language {settings.language!r}')
    return []


def _play_media(media_id: str, request_lang: str, hidden: bool):
    """Play a media file"""

    cached = _MultiLangMediaCache(media_id, hidden=hidden)

    title_languages = _get_title_language(request_lang)
    title_item = cached.get(title_languages)

    playback_languages = _get_playback_language(request_lang, is_video=title_item.type == MEDIA_VIDEO)
    playback_item = cached.get(playback_languages)

    list_item = create_media_item(title_item)
    list_item.url = get_best_url(playback_item)
    list_item.subtitles = _get_subtitles(cached)  # TODO need to append subtitles for video's native language?

    # Start playing
    kodi().set_resolved_url(list_item)

    if list_item.subtitles:
        playback_language = playback_item.session.language
        want_subtitles = _get_subtitle_visibility(playback_language)
        _set_subtitle_visibility(want_subtitles)


def play_endpoint(request: PlayRequest):
    """API endpoint that plays a media file, or redirects to get language agnostic watch status"""

    if request.lang and not request.no_redirect and not request.hidden:
        settings.tmp_language = request.lang
        kodi().execute('PlayMedia(' + PlayRequest(media=request.media, hidden=False).url + ', resume)')
    else:
        _play_media(request.media, request.lang or settings.tmp_language, hidden=request.hidden)
        settings.tmp_language = ''
