from __future__ import annotations

from typing import Optional
from urllib.error import HTTPError

from . import const
from ._api_responses import CategoryResponse, LanguageResponse, MediaResponse, RootResponse, TranslationResponse
from ._api_responses import CompleteCategoryDict, LanguageDict, MediaDict
from ._api_responses import NotFoundError
from .._request import get_json as _unsafe_get_json

API_BASE = 'https://b.jw-cdn.org/apis/mediator/v1'

# -------
# Globals
# -------

# Default value of subcatmedialimit (grep that to see where it's used)
#
# This limit tracks how big the list of subcategory media can be in a single response.
# It is used by Category.get_media() to know if it needs to send more requests to get the full media list.
#
# The API provides no way of knowing if the subcategory media list is capped, like it does for the main
# media list by providing a totalCount. We just have to guess if there seems to be a max limit by looking
# at all responses and using the biggest one as a reference. The API _does_ report a limit of 500 for
# the main media list, but we don't know if that will apply to subcategories too...
#
# Historically the reported main limit has been lower, and then increased before any category got more
# items than the limit, so we can't know if they will keep doing that (though 500 is a lot)...
#
# As of 2026-09 it seems like no subcategory has been capped by a limit.
# The category `VODPgmEvtMorningWorship` serves 380+ items in a single response.
#
# To play it safe we default to a low limit. This might result in a few extra requests when parsing the tree,
# but in return it is more future-proof, in case the server side decides to lower the limit.
# If the server goes lower that this limit, it will break jwlib in two ways:
# - subcategories won't detect if the media list is capped/incomplete
# - the media list would differ depending on _how_ the category was created (directly vs from subcategory)
#
_inferred_subcategory_media_limit = 100


def get_inferred_media_limit() -> int:
    return _inferred_subcategory_media_limit


def set_inferred_media_limit(limit: int) -> None:
    global _inferred_subcategory_media_limit
    _inferred_subcategory_media_limit = limit


# ---------
# Functions
# ---------

def get_json(url: str, query: Optional[dict] = None, *, headers: Optional[dict] = None):
    try:
        return _unsafe_get_json(url, query, headers=headers)
    except HTTPError as e:
        if e.code == 404:
            raise NotFoundError from e
        raise


def fetch_top_level(language: str, client: str) -> list[CompleteCategoryDict]:
    """Request list of top-level categories from the server"""

    # Never call this with detailed=1
    # It results in 'subcategories': {} which is a TypeError (should be a list)
    # This is a bug on the server side
    query = {'clientType': client if client != const.CLIENT_NONE else None}
    try:
        response: RootResponse = get_json(f'{API_BASE}/categories/{language}', query)
        return response['categories']
    except (NotFoundError, KeyError) as e:
        raise NotFoundError(f'{language}/') from e


def fetch_category_dict(language: str, key: str, *, client: str, include_media: bool,
                        media_list_offset=0) -> tuple[CompleteCategoryDict, int]:
    """Request category data from the server"""

    assert language
    assert key
    assert key != const.ROOT_CATEGORY

    query = {
        'clientType': client if client != const.CLIENT_NONE else None,
        # detailed controls whether subcategories will be included in the response
        # None means no, anything else means yes
        'detailed': 1,
        # offset controls at which index the media list will start
        # this is useful in case the total length is larger than 'limit'
        'offset': (media_list_offset or None) if include_media else None,
        # limit controls the max length of the media list
        # None means the server will decide
        'limit': None if include_media else 0,
        # mediaLimit controls the max length of the media list inside subcategories
        # None means the server will decide
        'mediaLimit': None if include_media else 0,
    }
    try:
        response: CategoryResponse = get_json(f'{API_BASE}/categories/{language}/{key}', query)

        # The more correct way would be to return UNSET on failure, but if we do so, there is no way to actually
        # get the media count anyway, which might result in an infinite loop, so we just return 0
        # and pretend like everything is fine
        media_count: int = response.get('pagination', {}).get('totalCount', 0)

        # Increment subcatmedialimit (grep that for more info).
        subcat_media_counts = (len(sc.get('media', []))
                               for sc in response.get('category', {}).get('subcategories', []))
        max_subcat_media_count = max(subcat_media_counts, default=0)
        set_inferred_media_limit(max(max_subcat_media_count, get_inferred_media_limit()))

        return response['category'], media_count
    except (NotFoundError, KeyError) as e:
        raise NotFoundError(f'{language}/{key}') from e


def fetch_media_dict(language: str, key: str, *, client: str) -> MediaDict:
    """Request media data from the server"""

    assert language
    assert key

    try:
        query = {'clientType': client if client != const.CLIENT_NONE else None}
        response: MediaResponse = get_json(f'{API_BASE}/media-items/{language}/{key}', query)
        return response['media'][0]
    except (NotFoundError, IndexError) as e:
        raise NotFoundError(f'{language}/{key}') from e


def fetch_languages(language: str) -> list[LanguageDict]:
    assert language

    response: LanguageResponse = get_json(f'{API_BASE}/languages/{language}/web')
    return response['languages']


def fetch_translations(language: str) -> dict[str, str]:
    assert language

    response: TranslationResponse = get_json(f'{API_BASE}/translations/{language}')
    return response['translations'][language]
