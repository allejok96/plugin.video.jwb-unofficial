from resources.lib.jwgui import create_category_item, create_media_item
from resources.lib.jwapi import is_convention_release_root, get_content_multilanguage
from resources.lib.kodi import kodi
from resources.lib.requests import BrowseRequest
from resources.lib.settings import settings
from resources.lib.translations import *


def _is_unseen_convention(category: str) -> bool:
    """Safety question for convention releases"""
    return (is_convention_release_root(category)
            and not kodi().question_dialog('', tr(Have_you_attended_the_convention)))


def browse_endpoint(request: BrowseRequest) -> None:
    """API endpoint that shows a page of subcategories and/or media"""

    if _is_unseen_convention(request.category):
        return

    subcategories, media = get_content_multilanguage(
        category=request.category,
        languages=[settings.language, settings.fallback_language],
        hidden=request.hidden,
        include_media=request.media,
    )

    kodi().add_items([create_category_item(sc) for sc in subcategories]
                     + [create_media_item(m) for m in media])
