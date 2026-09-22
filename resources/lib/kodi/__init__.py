from typing import Optional

from .abstract import ItemType, ListItem, LogLevel, KodiInterface

__all__ = (
    'ItemType',
    'ListItem',
    'LogLevel',
    'KodiInterface',
    'kodi',
)

instance: Optional[KodiInterface] = None


def kodi() -> KodiInterface:
    global instance

    if instance is None:
        from .real import RealKodiInterface
        real = RealKodiInterface()
        instance = real
        return real

    return instance
