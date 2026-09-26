import logging
from typing import List, Callable, Tuple

from resources.lib.jwapi import get_session
from resources.lib.kodi import kodi
from resources.lib.settings import settings, SubtitleMode, update_search_translation

logger = logging.getLogger(__name__)


def _upgrade_video_res() -> None:
    old_res = int(kodi().get_setting('video_res'))
    logger.info(f"Old value: {old_res}")

    # Old video resolution used an enum and the order was backwards
    new_res = {0: 1080, 1: 720, 2: 480, 3: 360, 4: 240}[old_res]
    logger.info(f"New value: {new_res}")

    settings.resolution = new_res


def _get_name_of_language(code: str) -> str:
    return next(f'{language.name} / {language.vernacular}'
                for language in get_session(hidden=False).get_languages()
                if language.code == code)


def _upgrade_remember_lang() -> None:
    # "Always use last selected language"
    # Activating this meant that the temp language never got cleared,
    # thus it would act like "Play in another language" was used every time.
    # (Playing in another language's audio with native subtitles).
    old_remember_lang = kodi().get_setting_bool('remember_lang')
    tmp_lang = settings.tmp_language

    logger.info(f'Old value: {old_remember_lang}')
    logger.info(f'Last language: {tmp_lang!r}')

    # If the user had this setting active and wanted to play a video in their native language
    # they would select that in the list of "Play in another language".
    # In that case it would be the same as if the setting was off.
    if old_remember_lang and tmp_lang and tmp_lang != settings.language:
        logger.info(f'Enabling original audio language: {tmp_lang}')

        try:
            label = _get_name_of_language(tmp_lang)
        except Exception:
            logger.debug(f'Failed to get full name of language {tmp_lang!r}')
            label = tmp_lang

        settings.original_audio = True
        settings.set_second_language(tmp_lang, label)

    else:
        logger.info(f'Disabling original audio language')
        settings.original_audio = False


def _upgrade_subtitles() -> None:
    # "Display subtitles by default"
    # This would enable subtitles for the native language
    # (When playing in another language, subtitles was always on by default)

    old_subtitles = kodi().get_setting_bool('subtitles')
    logger.info(f'Old value: {old_subtitles}')

    if old_subtitles:
        logger.info(f'Enabling subtitles for all languages')
        settings.subtitle_mode = SubtitleMode.ON
    else:
        logger.info(f'Enabling subtitles for original language and foreign languages')
        settings.subtitle_mode = SubtitleMode.ORIG_AND_FOREIGN


def _upgrade_empty_search_label() -> None:
    """The old addon allowed an empty search label, now we don't"""
    update_search_translation(settings.language)


# Order to run upgrade routines
# Length of this list affects settings version
# Do NOT remove or reorder items, only append
_upgrade_routines: List[Tuple[Callable[[], None], str]] = [
    (_upgrade_video_res, 'Migrating old video resolution setting'),
    (_upgrade_remember_lang, 'Migrating "Always use last selected language" setting'),
    (_upgrade_subtitles, 'Migrating old subtitle setting'),
    (_upgrade_empty_search_label, 'Updating cached translations'),
]


def migrate_settings() -> bool:
    """Migrate settings and return success"""

    current_settings_version = len(_upgrade_routines)

    try:
        last_settings_version = settings.settings_version
    except Exception as e:
        logger.info('Failed to read settings version', exc_info=e)
        settings.settings_version = current_settings_version
        return False

    if last_settings_version >= current_settings_version:
        return True

    logger.info(f'Starting settings migration {last_settings_version} => {len(_upgrade_routines)}')

    success = True
    for i in range(last_settings_version, current_settings_version):
        routine, description = _upgrade_routines[i]
        logger.info(description)
        try:
            routine()
        except Exception as e:
            logger.info(f'{description} - failed', exc_info=e)
            success = False

    settings.settings_version = current_settings_version
    logger.info(f'Settings migration finished')

    return success
