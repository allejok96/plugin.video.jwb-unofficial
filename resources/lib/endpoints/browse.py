from typing import List

from resources.lib.jwlib.media import Category

from resources.lib.jwgui import create_category_item, create_media_item
from resources.lib.jwapi import is_convention_release_root, get_category_multilanguage
from resources.lib.kodi import ListItem, kodi, ItemType
from resources.lib.requests import BrowseRequest
from resources.lib.settings import settings
from resources.lib.translations import *

__all__ = (
    'browse_endpoint',
)


def is_unseen_convention(category: str) -> bool:
    """Safety question for convention releases"""
    return (is_convention_release_root(category)
            and not kodi().question_dialog('', tr(Have_you_attended_the_convention)))


def merge_category_items(cats: List[Category]) -> List[ListItem]:
    """Extract unique ListItems from one or more categories (different languages)

    Duplicate items are ignored (language agnostic), only the first occurrence is kept.

    """
    seen_cats: List[str] = []
    seen_media: List[str] = []
    items: List[ListItem] = []

    for cat in cats:
        for subcat in cat.get_subcategories():
            if subcat.key not in seen_cats:
                seen_cats.append(subcat.key)
                items.append(create_category_item(subcat))
        for media in cat.get_media():
            if media.key not in seen_media:
                seen_media.append(media.key)
                items.append(create_media_item(media))

    return items

def sort_items_in_place(items: List[ListItem]):
    """Sort newest first and folders on top"""
    items.sort(key=lambda item: (item.type is ItemType.FOLDER, item.date), reverse=True)


def browse_endpoint(request: BrowseRequest) -> None:
    """API endpoint that shows a page of subcategories and/or media"""

    if is_unseen_convention(request.category):
        return

    cats = get_category_multilanguage(
        category=request.category,
        languages=[settings.language, settings.fallback_language],
        hidden=request.hidden,
        include_media=False,
    )

    items = merge_category_items(cats)

    sort_items_in_place(items)

    kodi().add_items(items)
