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


def show_whats_new() -> None:
    if settings.last_used_version < VERSION:
        kodi().text_dialog(f"New features in version {VERSION}", NEWS)


def mark_whats_new_as_shown() -> None:
    settings.last_used_version = kodi().get_addon_version()
