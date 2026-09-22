import warnings
from typing import TypeVar, Iterator

_T = TypeVar('_T')

class IteratorCompatibleList(list):
    """Monkey patched list that supports next()

    Old version of get_categories() returned a generator.
    Old version of get_media() returned a custom iterator.
    This version returns a list.

    The both are interchangeable most of the time, except when using next().
    """

    __iterator: Iterator

    def __next__(self):
        warnings.warn(
            f'Calling next() here is deprecated, use [0] instead',
            category=DeprecationWarning,
            stacklevel=2,
        )
        try:
            return next(self.__iterator)
        except AttributeError:
            self.__iterator = iter(self)
            return next(self.__iterator)
