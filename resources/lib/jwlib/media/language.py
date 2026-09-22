"""
Module kept for compatibility
"""
import warnings

from . import request_languages
from ._language import Language

__all__ = 'request_languages', 'Language'


warnings.warn(
    "Importing jwlib.media.language is deprecated, see jwlib.media.",
    category=DeprecationWarning,
)

