"""
Wrappers for the "mediator" API used in the video section at `jw.org <http://jw.org>`_.

Start a new session by calling `get_session()` with your language of choice.
Call `Session.get_category()` without arguments to get the root category.
Work your way from there using `Category.get_subcategories()` and `Category.get_media()`.

.. doctest::

    >>> import jwlib.media
    >>> session = jwlib.media.get_session(language='E')
    >>> broadcasting = session.get_category('VODStudio')
    >>> for subcategory in broadcasting.get_subcategories():
    >>>     for media in subcategory.get_media():
    >>>         file = media.get_file()
    >>>         print(media.title, file.url)
"""
from typing import List, Dict

from . import const
from ._api_responses import NotFoundError
from ._category import Category
from ._file import File
from ._language import Language
from ._media import Media
from ._session_base import BaseSession
from ._session_impl import Session
from ._subtitles import Subtitles
from .const import *  # TODO this should not be here, but is kept for backwards compatibility
from .._deprecated import deprecated as _deprecated

__all__ = (
    'const',

    'BaseSession',
    'Category',
    'File',
    'Language',
    'Media',
    'NotFoundError',
    'Session',
    'Subtitles',

    'get_session',
    'request_languages',
    'request_translations',
)


def get_session(language='E', client_type=const.CLIENT_FIRETV) -> BaseSession:
    """Set up a session used to fetch `Category` and `Media`.

    :param language: JW language code, see `Session.get_languages()`.
    :param client_type: To get as much data as possible (slower) use `const.CLIENT_NONE <jwlib.media.const>`.
    """
    return Session(language, client_type)


# ---------------------------
# For backwards compatibility
# ---------------------------


@_deprecated("Use `Session.get_languages()` instead")
def request_languages(language='E') -> List[Language]:
    return get_session(language=language).get_languages()


@_deprecated("Use `Session.get_translations()` instead")
def request_translations(language='E') -> Dict[str, str]:
    return get_session(language=language).get_translations()
