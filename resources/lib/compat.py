from typing import List, Callable

from resources.lib.jwapi import get_session
from resources.lib.kodi import kodi
from resources.lib.settings import settings, SubtitleMode

__all__ = (
    'migrate_settings',
)


def _upgrade_video_res() -> None:
    # Old video resolution used an enum and the order was backwards
    RES_ENUM = {0: 1080, 1: 720, 2: 480, 3: 360, 4: 240}
    old_res = int(kodi().get_setting('video_res'))

    if old_res == 0:  # default
        return

    try:
        kodi().log("Migrating legacy video resolution setting")
        settings.resolution = RES_ENUM[old_res]
    except Exception:
        kodi().log("Failed to migrate video resolution setting")


def _get_name_of_language(code: str) -> str:
    return next(f'{language.name} / {language.vernacular}'
                for language in get_session(hidden=False).get_languages()
                if language.code == code)


def _upgrade_remember_lang() -> None:
    # "Always use last selected language"
    # Activating this meant that the temp language never got cleared,
    # thus it would act like "Play in another language" was used every time.
    # (Playing in another language's audio with native subtitles).

    if not kodi().get_setting_bool('remember_lang'):  # default
        return

    tmp_lang = settings.tmp_language

    # If the user had this setting active and wanted to play a video in their native language
    # they would select that in the list of "Play in another language".
    # In that case it would be the same as if the setting was off.
    if tmp_lang == settings.language:
        return

    kodi().log('Migrating legacy "Always use last selected language" setting')

    try:
        label = _get_name_of_language(tmp_lang)
    except Exception:
        label = tmp_lang

    settings.set_second_language(tmp_lang, label)
    settings.original_audio = True


def _upgrade_subtitles() -> None:
    # "Display subtitles by default"
    # This would enable subtitles for the native language
    # (When playing in another language, subtitles was always on by default)

    if not kodi().get_setting_bool('subtitles'):  # default
        return

    kodi().log("Migrating legacy subtitle setting")
    settings.subtitle_mode = SubtitleMode.ON


# Order to run upgrade routines
# Length of this list affects settings version
# Do NOT remove or reorder items, only append
_upgrade_routines: List[Callable[[], None]] = [
    _upgrade_video_res,
    _upgrade_remember_lang,
    _upgrade_subtitles,
]


def _get_last_version() -> int:
    return int(kodi().get_setting('last_settings_version'))


def _set_last_version(val: int) -> None:
    kodi().set_setting('last_settings_version', str(val))


def migrate_settings() -> None:
    last_upgrade_routine_count = _get_last_version()

    if last_upgrade_routine_count >= len(_upgrade_routines):
        return

    for i in range(last_upgrade_routine_count, len(_upgrade_routines)):
        _upgrade_routines[i]()

    _set_last_version(len(_upgrade_routines))
