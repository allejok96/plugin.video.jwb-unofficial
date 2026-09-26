from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Union, Optional, TYPE_CHECKING, Iterable

from . import const
from ._api_requests import get_inferred_media_limit
from ._image_item import ItemWithImages
from ._iterator_compat import IteratorCompatibleList
from ._media import Media
from .._deprecated import deprecated

if TYPE_CHECKING:
    from ._session_base import BaseSession


@dataclass
class Category(ItemWithImages):
    """Category info, including subcategories and media.

    Use `Session.get_category()` or `Category.create()` to create an instance.
    """

    description: str
    """Category description, seems to be empty for the most part."""

    key: str
    """Code name.

    This is the code that can be passed to `Session.get_category()`.
    """

    media: list[Media]
    """List of media items.

    Lazy loaded - use `get_media()` to read it.
    """

    media_count: Optional[int]
    """Total number of available media items.

    Used for lazy-loading.
    """

    name: str
    """Display name."""

    parent: Optional[str]
    """Parent category key.

    Lazy loaded - use `get_parent()` to read it.
    """

    session: BaseSession
    """Session used to fetch media, parent and subcategory info as needed."""

    subcategories: Optional[list[str]]
    """List of subcategory keys.

    Lazy loaded - use `get_subcategories()` to read it.
    """

    type: const.CategoryType
    """Category type.

    - ``container`` if it has subcategories
    - ``ondemand`` if it has media
    """

    @staticmethod
    def create(*,
               description='',
               images: Optional[dict] = None,
               key: str,
               media: Optional[Iterable[Union[Media, dict]]] = None,
               media_count: Optional[int] = None,
               name='',
               parent: Optional[str] = None,
               session: BaseSession,
               subcategories: Optional[Iterable[str]] = None,
               tags: Optional[Iterable[str]] = None,
               type: const.CategoryType
               ) -> Category:
        return Category(
            description=description,
            images=images if images is not None else {},
            key=key,
            media=[m if isinstance(m, Media) else Media.create(**m, session=session) for m in media or []],
            media_count=media_count,
            name=name,
            parent=parent,
            session=session,
            subcategories=list(subcategories) if subcategories is not None else None,
            tags=list(tags) if tags is not None else [],
            type=type,
        )

    def __repr__(self):
        try:
            return f"<{self.__class__.__name__} '{self.session.language}/{self.key}'>"
        except Exception:
            return super().__repr__()

    @property
    @deprecated("Use `dataclasses.asdict()` instead.")
    def data(self) -> dict:
        return asdict(self)

    def get_media(self) -> list[Media]:
        """Return list of `Media` items.

        If `media` is unset or truncated, it will be requested from the server.
        """
        if not isinstance(self.media, IteratorCompatibleList):
            self.media = IteratorCompatibleList(self.media)

        # If we have to do more than 20 requests, something is wrong
        for i in range(20):
            if self._has_all_media():
                break

            chunk, total = self.session.request_category_media(self.key, offset=len(self.media))
            self.media.extend(chunk)
            self.media_count = total

            # Stop when there is nothing more to get
            if len(chunk) == 0:
                break

        # Make sure this never runs again
        self.media_count = len(self.media)
        return self.media

    def get_parent(self) -> Optional[Category]:
        """Return parent `Category`.

        If `parent` is unset, it will be requested from the server.
        """
        if self.key == const.ROOT_CATEGORY:
            return None
        elif self.parent is None:
            # If we are traversing up, we assume we won't be traversing down again,
            # so skip media to save some time
            self._refresh(include_media=False)
        if self.parent is not None:
            return self.session.get_category(self.parent)
        else:
            raise RuntimeError("Failed to fetch parent category")

    def get_subcategories(self, *, include_media=True) -> list[Category]:
        """Return list of subcategories.

        If `subcategories` is unset, it will be requested from the server.

        :param include_media: see `Session.get_category()`

        .. note::
            The returned list is temporary. To make persistent changes, write to `subcategories`.
        """
        if self.subcategories is None:
            if self.type == const.CATEGORY_CONTAINER:
                self._refresh(include_media=include_media)
            else:
                self.subcategories = []
        if self.subcategories is not None:
            return IteratorCompatibleList(self.session.get_category(key) for key in self.subcategories)
        else:
            raise RuntimeError("Failed to fetch subcategories")

    @deprecated("To truly refresh a category, delete if from `Session.categories`.")
    def refresh(self, *, include_media=True) -> None:
        self._refresh(include_media=include_media)

    # -------
    # Private
    # -------

    def _has_all_media(self):
        # Non-on-demand categories have no media
        if self.type != const.CATEGORY_ONDEMAND:
            return True

        # We reached the expected amount
        if self.media_count is not None and len(self.media) >= self.media_count:
            return True

        # Check subcatmedialimit (grep that for more info)
        #
        # If the category came from a subcategory (media_count is None), and it contains media,
        # and it's not capped at the limit, then we can assume we have all media.
        #
        # Why not use `0 < len(media) < inferred_limit` ?
        # For regular use overshooting the inferred limit cannot happen, because the function that parses the
        # subcategory media, will update the inferred limit accordingly. And as soon as media is taken from NON
        # subcategory data, we will get an explicit media_count. But it IS possible to overshoot the inferred limit
        # if a user manually writes to the media list without editing media_count, so we need to account for that,
        # and assume that means we have all media.
        #
        if self.media_count is None and len(self.media) not in (0, get_inferred_media_limit()):
            return True

        # Tags like 'LimitToFive' govern how long the list should be.
        # In the case of FeaturedSetTopBoxes the list is actually longer, but to get all items
        # you have to send multiple request, so we obey the tag when it appears.
        for limit, tag in enumerate(const.TAGS_ITEM_LIMIT):
            if tag in self.tags and len(self.media) >= limit:
                return True

        return False

    def _refresh(self, *, include_media=True) -> None:
        new = self.session.request_category(self.key, include_media=include_media)
        update_category(self, new)


def update_category(cat: Category, other: Category) -> None:
    """Set the missing values in one category using another category

    This runs whenever fresh category data is gathered from a parent, subcategory, or a direct call to get_category.
    It also runs when refresh() is called to update missing data for get_media() or get_subcategories().

    We only want to update MISSING values, so that a refresh of another category does not overwrite
    explicitly set values of this category.

    Category.media is a bit special since the default value is [] instead of None, so we can't differentiate
    unset from empty, but it doesn't matter that much in this case. Well, it would matter if the user wanted to
    remove all media and not have it update back. But in any case they would have to set media_count to 0 too.
    """
    if not cat.media:
        cat.media = other.media
    if cat.media_count is None:
        cat.media_count = other.media_count
    if cat.parent is None:
        cat.parent = other.parent
    if cat.subcategories is None:
        cat.subcategories = other.subcategories
