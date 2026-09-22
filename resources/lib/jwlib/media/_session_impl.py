from __future__ import annotations

import logging
from typing import Optional, Iterable

from . import const
from ._api_requests import fetch_media_dict, fetch_languages, fetch_translations, fetch_category_dict, fetch_top_level
from ._api_responses import PartialCategoryDict, BasicCategoryDict, CompleteCategoryDict
from ._category import Category, update_category
from ._category_factory import create_partial, create_basic, create_root
from ._language import Language
from ._language_factory import create_language
from ._media import Media
from ._media_factory import create_media
from ._session_base import BaseSession
from .._deprecated import deprecated

__all__ = (
    'Session',
)

logger = logging.getLogger(__name__)


class Session(BaseSession):
    """This implements a session that can make requests to the jw.org media API.

    To create a new instance, use `get_session()`.

    If you want to create a dummy session for testing, derive it from `BaseSession`.
    """
    # --------------
    # Public methods
    # --------------

    def get_languages(self) -> list[Language]:
        """Return a list of `Language` info for all available languages."""
        return [create_language(ld) for ld in fetch_languages(self.language)]

    def get_media(self, key: str) -> Media:
        """Return a `Media` item.

        Unlike `get_category()` this is not cached.
        """
        return create_media(
            fetch_media_dict(language=self.language, key=key, client=self.client_type),
            parent=None,
            session=self,
        )

    def get_translations(self) -> dict[str, str]:
        """Return a dict of string IDs and translations used at the website"""
        return fetch_translations(self.language)

    def request_category(self, key: str, *, include_media=True) -> Category:
        """Implementation of request_category

        :meta private: mainly needed for internal use, no need for documentation
        """
        if key == const.ROOT_CATEGORY:
            has_requested_root_before = const.ROOT_CATEGORY in self.categories
            root = self._add_root()
            if has_requested_root_before:
                root.subcategories = [self._add_basic(sc_data, parent=const.ROOT_CATEGORY).key
                                      for sc_data in fetch_top_level(self.language, self.client_type)]
        else:
            cat_dict, media_count = fetch_category_dict(
                self.language,
                key,
                client=self.client_type,
                include_media=include_media
            )
            self._add_complete(cat_dict, media_count=media_count)

        return self.categories[key]

    def request_category_media(self, key: str, offset: int) -> tuple[list[Media], int]:
        """Implementation of request_category_media

        :meta private: mainly needed for internal use, no need for documentation
        """
        category_page, media_count = fetch_category_dict(
            self.language,
            key,
            client=self.client_type,
            include_media=True,
            media_list_offset=offset
        )

        media = [create_media(md, parent=key, session=self) for md in category_page.get('media', [])]
        return media, media_count

    # ---------------
    # Private methods
    # ---------------

    def _add_complete(self, d: CompleteCategoryDict, *, media_count: int) -> Category:

        parent_dict = d['parentCategory']
        if parent_dict is None:
            parent_key = const.ROOT_CATEGORY
        else:
            parent_key = parent_dict['key']
            self._add_basic(parent_dict, parent=None)

        cat = create_partial(d, media_count=media_count, parent=parent_key, session=self)
        cat.subcategories = [self._add_partial(subcat_dict, media_count=None, parent=cat.key).key
                             for subcat_dict in d.get('subcategories', [])]

        return self._add_or_update(cat)

    def _add_partial(self, d: PartialCategoryDict, *,
                     media_count: Optional[int],
                     parent: Optional[str]) -> Category:

        return self._add_or_update(
            create_partial(d, media_count=media_count, parent=parent, session=self)
        )

    def _add_basic(self, d: BasicCategoryDict, *, parent: Optional[str]) -> Category:
        return self._add_or_update(
            create_basic(d, parent=parent, session=self)
        )

    def _add_root(self) -> Category:
        if const.ROOT_CATEGORY not in self.categories:
            self.categories[const.ROOT_CATEGORY] = create_root(session=self)
        return self.categories[const.ROOT_CATEGORY]

    def _add_or_update(self, other: Category) -> Category:
        if other.key in self.categories:
            update_category(self.categories[other.key], other)
        else:
            self.categories[other.key] = other
        return self.categories[other.key]

    # ----------
    # Deprecated
    # ----------

    @deprecated("Use `Session.categories.values()` instead.")
    def cached_categories(self) -> Iterable[Category]:
        return self.categories.values()

    @deprecated("Use `Category.create()` instead (construction from API data is no longer public).")
    def create_category(self, category_data: CompleteCategoryDict, *, parent_key: Optional[str] = None) -> Category:
        try:
            media_count = len(category_data.get('media', []))
            return self._add_complete(category_data, media_count=media_count)
        except KeyError:
            return self._add_partial(category_data, media_count=None, parent=parent_key)

    @deprecated("Use `get_media()` instead.")
    def request_media(self, key: str) -> Media:
        return self.get_media(key)

