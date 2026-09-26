from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
from typing import Iterable

from . import const
from ._category import Category
from ._language import Language
from ._media import Media


class BaseSession(ABC):
    """Abstract base class of Session.

    Useful if you need to create mock sessions for testing,
    or other custom behavior.

    For regular use, see `Session`.
    """

    categories: dict[str, Category]
    """Cached categories, indexed by `Category.key`.

    See `get_category()`.
    """

    client_type: str
    """Client type, affects available images and media.

    See `const.CLIENT_* <jwlib.media.const>`
    """

    language: str
    """JW language code."""

    def __init__(self, language: str = 'E', client_type: str = const.CLIENT_FIRETV):
        self.language = language
        self.client_type = client_type
        self.categories: dict[str, Category] = {}

    # ================
    # Cache management
    # ================

    def load_categories(self, cache: Iterable[dict]) -> None:
        """Load categories from a cache dump."""
        for category_data in cache:
            cat = Category.create(**category_data, session=self)
            self.categories[cat.key] = cat

    def dump_categories(self) -> list[dict]:
        """Dump category cache to a format that may be serialized to JSON."""

        dump = []
        for cat in self.categories.values():
            cat_dict = asdict(cat, dict_factory=lambda pairs: dict(filter(lambda pair: pair[0] != 'session', pairs)))
            dump.append(cat_dict)
        return dump

    # ==============
    # Public getters
    # ==============

    def get_category(self, key=const.ROOT_CATEGORY, *, include_media=True) -> Category:
        """Get a `Category` from cache or request it if missing.

        :param key: Code name.
        :param include_media: Setting this to False may speed up JSON parsing significantly
            for some categories, but will result in extra requests if `get_media()` is called later.
        """
        if key not in self.categories:
            self.categories[key] = self.request_category(key, include_media=include_media)

        return self.categories[key]

    @abstractmethod
    def get_languages(self) -> list[Language]:
        """Return list of language info.

        Must be implemented by child class.
        """
        ...

    @abstractmethod
    def get_media(self, key: str) -> Media:
        """Return a media item.

        Must be implemented by child class.
        """
        ...

    @abstractmethod
    def get_translations(self) -> dict[str, str]:
        """Return a dictionary of string IDs paired with translations.

        Must be implemented by child class.
        """
        ...

    # ============
    # Semi-private
    # ============

    @abstractmethod
    def request_category(self, key: str, *, include_media=True) -> Category:
        """Create a new category instance.

        Called by `get_category()` when a category is missing from the cache.

        Must be implemented by child class.
        """
        ...

    @abstractmethod
    def request_category_media(self, key: str, *, offset: int) -> tuple[list[Media], int]:
        """Return a list of media for the given category, along with the total count.

        :param offset: is used to get the next "page" of very long lists.

        Called by `Category.get_media()` when the media list is missing or incomplete.

        Must be implemented by child class.
        """
        ...
