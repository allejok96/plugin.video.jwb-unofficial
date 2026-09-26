import re
from typing import Tuple

from resources.lib.kodi import kodi
from resources.lib.settings import settings

VERSION = '2.0.0'

NEWS = """
- Original audio
  Enable this setting to watch videos in English with subtitles in your language.

- Fallback language
  Enable this setting to include videos that are not available in your language yet.

- Shuffle in another language
  You can find this in the context menu of categories.
"""


def _parse_version(version: str) -> Tuple[int, ...]:
    """Turn '2.10.1' into (2, 10, 1) so it can be compared numerically

    Anything after the numeric part (like '~beta1' or '+matrix.1') is ignored.
    An empty or invalid string gives (), which is lower than any version.
    """
    match = re.match(r'\d+(\.\d+)*', version)
    return tuple(int(n) for n in match.group().split('.')) if match else ()


def show_whats_new() -> None:
    if _parse_version(settings.last_used_version) < _parse_version(VERSION):
        kodi().text_dialog(f"New features in version {VERSION}", NEWS)
        mark_whats_new_as_shown()


def mark_whats_new_as_shown() -> None:
    settings.last_used_version = kodi().get_addon_version()
