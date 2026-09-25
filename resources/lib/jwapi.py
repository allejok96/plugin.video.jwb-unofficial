"""
Common functions to request and process jwlib data
"""
import logging
from typing import Optional, Union, List, Tuple

import resources.lib.jwlib.media as jwlib
from resources.lib.jwlib.media import BaseSession, Category, Media, File, NotFoundError
from resources.lib.jwlib.media.const import CLIENT_APPLETV, CLIENT_NONE, TAG_EXCLUDE_APPLETV

from resources.lib.settings import settings, SubtitleMode


logger = logging.getLogger(__name__)


def get_session(lang: str = '', *, hidden: bool) -> BaseSession:
    """Return a new Session, with correct language and client type"""

    client = CLIENT_NONE if hidden else CLIENT_APPLETV
    return jwlib.get_session(lang or settings.language, client)


def _rank_file(file: File) -> Tuple[bool, bool, int]:
    """Sort function for Files (best is last)"""

    is_subtitled = (file.subtitles is not None) or file.subtitled_hard
    good_subs = is_subtitled if settings.subtitle_mode == SubtitleMode.ON else not file.subtitled_hard
    reso = file.resolution or 0
    good_reso = 0 < reso <= settings.resolution
    return good_subs, good_reso, reso


def _unique_list(values: List[str]) -> List[str]:
    """Remove duplicate items from a list"""

    result = []
    for v in values:
        if v not in result:
            result.append(v)
    return result


def get_media(key: str, *, languages: List[str], hidden: bool) -> Media:
    """Look for Media in multiple languages, return first.

    Lookups are cached, empty language strings skipped.
    Raises error if no languages contained the Media.
    """

    assert any(languages)

    for lang in languages:
        if not lang:
            continue
        try:
            return get_session(hidden=hidden, lang=lang).get_media(key)
        except NotFoundError:
            logger.debug(f'Media not found: {lang}/{key}')
    raise NotFoundError


def get_best_url(m: Media) -> str:
    """Return the most suitable URL from a Media object"""

    return sorted(m.files, key=_rank_file, reverse=True)[0].url


def is_hidden(item: Union[Category, Media]) -> bool:
    """True if item is a convention release or other item that should not be visible on TV"""

    # The convention release category should not be hidden even though it has the EXCLUDE tag...
    # This is so it will be visible in the main menu.
    # If the user tries to open it, it will trigger a question.
    if isinstance(item, Category) and is_convention_release_root(item.key):
        return False

    return TAG_EXCLUDE_APPLETV in item.tags


def is_convention_release_root(cat: str):
    """True if this is the top-level category containing hidden convention releases

    TODO this might break if it changes name upstream, can we detect it using tags instead?
    """
    return cat == 'ConvReleases'


def get_category_multilanguage(category: str, languages: List[str], hidden: bool, include_media: bool) -> List[
    Category]:
    """Return list of Categories in ALL given languages, but ignore ones that cannot be found"""

    result: List[Category] = []
    for lang in _unique_list(languages):
        try:
            result.append(get_session(lang=lang, hidden=hidden).get_category(category, include_media=include_media))
        except NotFoundError:
            logger.debug(f'Category not found: {lang}/{category}')

    if not result:
        raise NotFoundError(f"Category {category} not found in languages {languages}")

    return result
