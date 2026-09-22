"""
Module kept for compatibility
"""


class NotFoundError(Exception):
    """Common base class for NotFoundErrors across jwlib.

    .. warning::
        Deprecated, use `jwlib.media.NotFoundError` (or similar) instead.
    """
    ...
