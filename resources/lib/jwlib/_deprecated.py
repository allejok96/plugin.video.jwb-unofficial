import functools
import warnings
from typing import Callable


def deprecated(reason: str):
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            warnings.warn(
                f'{func.__name__}: {reason}',
                category=DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)

        wrapper.__doc__ = wrapper.__doc__ or '' + '\n\n:meta private:'
        return wrapper

    return decorator
