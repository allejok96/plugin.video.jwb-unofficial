import random
from typing import Iterator, List, Set, Iterable

from resources.lib.jwlib.media import Category, Media
from resources.lib.jwlib.media.const import MEDIA_AUDIO

from resources.lib.jwapi import get_best_url, get_category_multilanguage
from resources.lib.jwgui import create_media_item, create_media_item_with_url
from resources.lib.kodi import kodi, ListItem
from resources.lib.requests import ShuffleRequest
from resources.lib.settings import settings


def _get_all_media(category: Category) -> Iterator[Media]:
    """Iterator of all media items, depth first"""

    for subcat in category.get_subcategories():
        yield from _get_all_media(subcat)
    yield from category.get_media()


def _get_unique_media_from_categories(categories: Iterable[Category]) -> List[Media]:
    seen_media: Set[str] = set()
    media = []
    for cat in categories:
        for m in _get_all_media(cat):
            if m.key not in seen_media:
                seen_media.add(m.key)
                media.append(m)
    return media


def _create_language_agnostic_media_item(media: Media, requested_lang: str) -> ListItem:
    # TODO language agnostic watch status for shuffle in another language
    # There are multiple possible solutions that I can think of that doesn't work
    # 1. Let the request redirect, just like play requests.
    #       This doesn't work because that would interrupt playlist playback.
    #       It might also crash due to bug #20964.
    # 2. Make lang_next sticky and add a parameter to standard media items to clear it.
    #       This would require that all standard items were redirected upon playback
    #       which would break "Play from here" and "Add to playlist", just as point 1.
    # 3. Make lang_next sticky and let other requests such as browse clear it.
    #       This *could* work, but it would break the current shuffle in another language
    #       if the user minimized the player and started browsing. In that case the videos
    #       would start playing in the default language instead.
    # 4. Passing extra info to ListItem.setProperty().
    #       This feels like a solution in theory, but it's a bit unclear whether it would work.
    #       The addon is not called with the list item about to be played, it's just called with
    #       a URL query. setResolvedURL() actually takes a *new* ListItem, so the one that ends
    #       up in the player is not the one in the playlist (in the cases setResolvedURL is used).
    #       Would it be possible to retrieve the current ListItem *before* the resolve happens?
    #       Idk, but it feels like a disaster waiting to happen.

    # We can only perform a regular language agnostic request if there is no explicit language set
    # because that would trigger a redirection that breaks playlist playback (see point 1 above)
    if not requested_lang:
        return create_media_item(media)

    # We can avoid the redirection by providing a direct URL.
    # This breaks the subtitle setting feature, but for audio that doesn't matter
    # The benefit is that it is faster to start playing the item
    elif media.type == MEDIA_AUDIO:
        return create_media_item_with_url(media, url=get_best_url(media))

    # The last option to avoid redirection is to provide the no_redirect= argument.
    # This breaks language agnostic watch status, though.
    # We must do this for videos to get proper subtitle settings
    # (since this is handled by the addon after setResolvedURL is called)
    else:
        return create_media_item(media, language=requested_lang, no_redirect=True)


def shuffle_endpoint(request: ShuffleRequest):
    """API endpoint that creates a playlist and starts playing"""

    cats = get_category_multilanguage(
        category=request.category,
        languages=[request.lang or settings.language, settings.fallback_language],
        hidden=request.hidden,
        include_media=True,
    )

    media = _get_unique_media_from_categories(cats)

    playlist = [_create_language_agnostic_media_item(m, request.lang) for m in media]

    # Shuffle in place, we don't want to mess with Kodi's settings
    random.shuffle(playlist)

    kodi().start_playlist(playlist)
