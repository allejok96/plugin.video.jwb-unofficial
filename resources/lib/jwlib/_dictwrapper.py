from __future__ import annotations

import logging
from typing import Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

_T = TypeVar('_T')


class _DictWrapper:
    """Wraps server response data"""

    data: dict
    """Object data as returned by the server.

    If you need access to information that has no getter method, you can get it here.

    .. note::
        Editing this directory is an untested feature.

    .. warning::
        Deprecated, will be removed in future versions.
    """

    def __init__(self, data: dict):
        if not isinstance(data, dict):
            raise TypeError(f'Argument must be a dict, not {type(data)}')
        self.data = data

    def _safe_get(self, key: str, default: Optional[_T], getter: Callable[[], _T]) -> _T:
        try:
            return getter()

        except KeyError as e:
            if default is None:
                raise KeyError(f'{self!r}.data[{key!r}] is missing') from e

        except (ValueError, TypeError) as e:
            if default is None:
                raise type(e)(f'{self!r}.data[{key!r}] cannot be {self.data[key]!r}') from e
            logger.debug(f'{self!r}.data[{key!r}] should not be {self.data[key]!r}, replacing with {default!r}')

        return default

    def _get_bool(self, key: str, default: Optional[bool] = None) -> bool:
        return self._safe_get(key, default, lambda: bool(self.data[key]))

    def _get_int(self, key: str, default: Optional[int] = None) -> int:
        return self._safe_get(key, default, lambda: int(self.data[key]))

    def _get_float(self, key: str, default: Optional[float] = None) -> float:
        return self._safe_get(key, default, lambda: float(self.data[key]))

    def _get_string(self, key: str, default: Optional[str] = None) -> str:
        """Return a non-zero string"""

        value = self._safe_get(key, default, lambda: self.data[key])

        if not isinstance(value, str):
            if default is None:
                raise TypeError(f'{self!r}.data[{key!r}] cannot be {value!r}')
            logger.debug(f'{self!r}.data[{key!r}] should not be {value!r}, replacing with {default!r}')

        elif value == '':
            if default is None:
                raise ValueError(f'{self!r}.data[{key!r}] cannot be an empty string')

        else:
            return value

        return default
