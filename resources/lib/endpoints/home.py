import logging
from pathlib import Path
from typing import List

from resources.lib.jwlib.media import Category, Language
from resources.lib.jwlib.media.const import ROOT_CATEGORY

from resources.lib.jwapi import is_hidden, get_category_multilanguage, get_session
from resources.lib.jwgui import create_category_item, show_disclaimer
from resources.lib.kodi import kodi, ListItem, ItemType
from resources.lib.requests import SearchRequest
from resources.lib.settings import settings

logger = logging.getLogger(__name__)


def _first_time_setup():
    if settings.first_run:
        settings.first_run = False
        _set_addon_lang_from_system_lang(kodi().get_system_language(), _try_get_jw_languages())
        show_disclaimer()


def _try_get_jw_languages() -> List[Language]:
    try:
        return get_session(hidden=False).get_languages()
    except Exception:
        logger.debug('Failed to fetch language list')
        return []


def _set_addon_lang_from_system_lang(iso_lang: str, jw_languages: List[Language]):
    """Set addon language to system language"""
    try:
        language = next(lang for lang in jw_languages if lang.iso == iso_lang)
    except StopIteration:
        logger.error(f'Failed to auto configure language to {iso_lang!r}')
        return

    settings.set_language(language.code, f'{language.name} / {language.vernacular}')


def _get_root_categories() -> List[Category]:
    # To see if there is a convention release page we need to show hidden items
    # TODO potential bug: if there are top level categories in fallback language but not in default language
    root = get_category_multilanguage(ROOT_CATEGORY, languages=[settings.language], hidden=True, include_media=False)[0]

    return [cat
            for cat in root.get_subcategories()
            if not is_hidden(cat)]


def _get_fanart_path() -> str:
    return str(Path(kodi().get_addon_path()) / kodi().get_addon_fanart())


def home_endpoint():
    """API endpoint for the main menu"""

    _first_time_setup()

    fanart = _get_fanart_path()
    cats = _get_root_categories()
    items = [create_category_item(c, fanart=fanart) for c in cats]

    items.append(ListItem(
        title=settings.search_label or 'Search',
        fanart=fanart,
        icon='DefaultMusicSearch.png',
        type=ItemType.FOLDER,
        url=SearchRequest().url,
    ))

    kodi().add_items(items)
