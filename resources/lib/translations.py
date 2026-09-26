"""
String IDs from strings.po
"""
from resources.lib.kodi import kodi as _kodi

Connection_error = 30300
Not_available_in_selected_language = 30301
Settings_migration_error = 30302
See_the_log = 30303
Theocratic_warning = 30310
Full_disclaimer = 30311
Hidden_item = 30320
Have_you_attended_the_convention = 30320
Play_in_another_language = 30400
Shuffle_this_category = 30401
Shuffle_in_another_language = 30402
Audio_clips = 30410
Page_nr = 30411


def tr(id: int) -> str:
    """Translate a string ID"""
    return _kodi().get_localized_string(id)
