"""
Functions to create onscreen ListItems from jwlib data
"""

from typing import List

from resources.lib.jwlib.media import Category, Media
from resources.lib.jwlib.media.const import MEDIA_AUDIO, CATEGORY_ONDEMAND
from resources.lib.jwlib.search import Result, DeepLink
from resources.lib.jwlib.search.const import TYPE_VIDEO_CAT, TYPE_AUDIO_CAT, TYPE_AUDIO

from resources.lib.requests import BrowseRequest, ShuffleRequest, LanguageRequest, PlayRequest
from resources.lib.jwapi import is_hidden
from resources.lib.kodi import ListItem, ItemType, kodi
from resources.lib.translations import *


def create_category_item(c: Category, *, fanart=None) -> ListItem:
    """Create a ListItem from a Category and add it to the screen"""

    hidden = is_hidden(c)
    image = c.get_image()

    return ListItem(
        title=c.name,
        description=c.description,
        icon=image,
        fanart=fanart,
        menu=[
            (tr(Shuffle_this_category), ShuffleRequest(category=c.key, hidden=hidden).url),
            (tr(Shuffle_in_another_language), LanguageRequest(shuffle_category=c.key, hidden=hidden).url)
        ],
        type=ItemType.FOLDER,
        url=BrowseRequest(category=c.key, hidden=hidden, media=_has_media(c)).url,
    )


def create_media_item_with_url(m: Media, *, url: str) -> ListItem:
    """Create a ListItem from Media, and set its URL manually"""

    return ListItem(
        title=m.title,
        date=m.published,
        description=m.description,
        duration=int(m.duration),
        icon=m.get_image(),
        menu=[
            (tr(Play_in_another_language), LanguageRequest(play_media=m.key, hidden=is_hidden(m)).url),
        ],
        type=ItemType.AUDIO if m.type == MEDIA_AUDIO else ItemType.VIDEO,
        url=url,
    )


def create_media_item(m: Media, *, language='', no_redirect=False) -> ListItem:
    """Create a ListItem from Media"""

    request = PlayRequest(media=m.key, hidden=is_hidden(m), lang=language, no_redirect=no_redirect)
    return create_media_item_with_url(m, url=request.url)


def create_search_result(r: Result) -> ListItem:
    """ListItem for search results"""

    if r.type in (TYPE_VIDEO_CAT, TYPE_AUDIO_CAT):
        # The keys look like: mc-VODChildren
        cat = r.key.replace('mc-', '')

        return ListItem(
            title=r.title,
            icon=r.image,
            type=ItemType.FOLDER,
            url=BrowseRequest(category=cat, hidden=False, media=False).url,
        )

    deep_links: List[DeepLink] = r.deep_links
    if deep_links:
        snippet = '\n\n'.join(f'{dl.label}\n{dl.snippet}' for dl in deep_links)
    else:
        snippet = r.snippet

    snippet = snippet.replace('<strong>', '[B]').replace('</strong>', '[/B]')

    return ListItem(
        r.title,
        description=snippet,
        duration=r.duration,
        icon=r.image,
        menu=[
            (tr(Play_in_another_language), LanguageRequest(play_media=r.key, hidden=False).url),
        ],
        type=ItemType.AUDIO if r.type == TYPE_AUDIO else ItemType.VIDEO,
        url=PlayRequest(media=r.key, hidden=False).url,
    )


def show_disclaimer():
    """Show theocratic warning popup"""
    kodi().text_dialog(tr(Theocratic_warning), tr(Full_disclaimer))


def _has_media(category: Category) -> bool:
    """True if we can expect to find media in this category"""

    return category.type == CATEGORY_ONDEMAND
