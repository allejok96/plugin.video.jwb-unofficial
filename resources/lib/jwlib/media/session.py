"""
Module kept for compatibility
"""
import warnings

from ._category import Category
from ._file import File
from ._media import Media
from ._session_impl import Session
from .const import *  # for compatibility

__all__ = 'Session', 'Category', 'Media', 'File'

warnings.warn(
    "Importing jwlib.media.session is deprecated, see jwlib.media.",
    category=DeprecationWarning,
)
