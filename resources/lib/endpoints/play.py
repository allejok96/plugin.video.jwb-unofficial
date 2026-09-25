import logging
import time
from typing import List, Dict, Set, Optional

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
                logger.debug(f'No media found for language {language!r}')
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


def _wait_for_playback_to_start(url: str) -> bool:
    for i in range(20):
        try:
            if kodi().get_playing_file() == url:
                return True
        except Exception:
            logger.debug('Waiting for playback to start...')
            time.sleep(1)
    return False


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
    list_item.subtitles = _get_subtitles(cached)

    # Start playing
    logger.debug(f'Resolving to: {list_item.url!r}')
    kodi().set_resolved_url(list_item)

    # Files may have subtitles baked in, so always set the visibility, even if the list item has no subtitles
    playback_language = playback_item.session.language
    want_subtitles = _get_subtitle_visibility(playback_language)
    logger.debug(f'Has external subtitles: {bool(list_item.subtitles)}')
    logger.debug(f'Want subtitles: {want_subtitles}')

    if _wait_for_playback_to_start(list_item.url):
        logger.debug(f'Setting subtitle visibility => {want_subtitles}')
        kodi().show_subtitles(want_subtitles)
    else:
        logger.warning('Not setting subtitle visibility, because playback never started')


def play_endpoint(request: PlayRequest):
    """API endpoint that plays a media file, or redirects to get language agnostic watch status"""

    if request.lang and not request.no_redirect and not request.hidden:
        settings.tmp_language = request.lang
        kodi().execute('PlayMedia(' + PlayRequest(media=request.media, hidden=False).url + ', resume)')
    else:
        if settings.tmp_language:
            language = settings.tmp_language
            settings.tmp_language = ''
        else:
            language = request.lang
        _play_media(request.media, language, hidden=request.hidden)
