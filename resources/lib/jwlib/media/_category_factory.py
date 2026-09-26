from typing import Optional

from . import const
from ._api_responses import PartialCategoryDict, BasicCategoryDict
from ._category import Category
from ._media_factory import create_media
from ._session_base import BaseSession


def create_partial(d: PartialCategoryDict, *,
                   media_count: Optional[int],
                   parent: Optional[str],
                   session: BaseSession) -> Category:
    media_parent = parent if isinstance(parent, str) else None
    cat = create_basic(d, parent=parent, session=session)

    # Possible values of 'media' returned by the server:
    # list[dict] - media info
    # empty list - requested with limit=0 or mediaLimit=0
    # unset - this category is not type 'ondemand', there is no media
    # unset - this comes from the top-level list, we need to request more info (could be LatestVideos etc)

    cat.media = [create_media(md, parent=media_parent, session=session) for md in d.get('media', [])]
    cat.media_count = media_count
    return cat


def create_basic(d: BasicCategoryDict, *, parent: Optional[str], session: BaseSession) -> Category:
    return Category(
        description=d.get('description', ''),
        images=d.get('images', {}),
        key=d['key'],
        media=[],
        media_count=None,
        name=d.get('name', ''),
        parent=parent,
        session=session,
        subcategories=None,
        tags=d.get('tags', []),
        type=d['type'],
    )


def create_root(*, session: BaseSession) -> Category:
    """Virtual root category

    The server has no "root" category, there's just a list of top-level categories.
    But we fake one so we can give it a name and a key for convenience.
    """
    return Category(
        description='Top-level category of all video and audio categories',
        images={},
        key=const.ROOT_CATEGORY,
        media=[],
        media_count=0,
        name='All Categories',
        parent=None,
        session=session,
        subcategories=None,
        tags=[],
        type=const.CATEGORY_CONTAINER,
    )
