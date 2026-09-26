"""
Wrapper for the `jw.org <http://jw.org>`_ search API.

.. doctest::

    >>> from jwlib.search import search
    >>> page = search('Caleb')
    >>> for r in page.results:
    >>>     print(r.title, r.url_jw)
"""

from . import const
from ._search import DeepLink, Result, ResultGroup, SearchInsight, ResultPage, PageLink, search
from .const import *  # for compatibility

__all__ = (
    'const',
    'search',
    'ResultPage',
    'ResultGroup',
    'Result',
    'PageLink',
    'DeepLink',
    'SearchInsight',
)
