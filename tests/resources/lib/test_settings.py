from resources.lib.settings import settings, SubtitleMode, append_to_language_history


def test_fallback_language():
    settings.set_language('E', 'English')
    settings.set_second_language('Z', 'Swedish')

    assert settings.enable_fallback is False  # default
    settings.enable_fallback = False
    assert settings.fallback_language == 'E'

    settings.enable_fallback = True
    assert settings.fallback_language == 'Z'


def test_first_run():
    assert settings.first_run is True  # default
    settings.first_run = False
    assert settings.first_run is False


def test_original_audio_language():
    settings.set_language('E', 'English')
    settings.set_second_language('Z', 'Swedish')

    settings.original_audio = False
    assert settings.original_audio_language == 'E'

    settings.original_audio = True
    assert settings.original_audio_language == 'Z'


def test_resolution(kodi):
    assert settings.resolution == 1080  # default
    settings.resolution = 720
    assert settings.resolution == 720


def test_subtitle_mode():
    assert settings.subtitle_mode == SubtitleMode.ORIG_AND_FOREIGN  # default
    settings.subtitle_mode = SubtitleMode.FOREIGN
    assert settings.subtitle_mode == SubtitleMode.FOREIGN


def test_token(kodi):
    assert settings.token == ''
    settings.token = 'ABC123'
    assert settings.token == 'ABC123'


def test_set_language(kodi, sessions):
    sessions.add('Z').translations =  {'hdgSearch': 'Sök'}

    assert settings.language == 'E'  # default
    settings.set_language('Z', 'Swedish')

    assert settings.language == 'Z'
    assert kodi.get_setting('lang_name') == 'Swedish'
    assert settings.search_label == 'Sök'


def test_set_second_language(kodi):
    assert settings.second_language == 'E'  # default
    settings.set_second_language('D', 'German')

    assert settings.second_language == 'D'
    assert kodi.get_setting('second_language_name') == 'German'


def test_tmp_language(kodi):
    assert settings.tmp_language == ''  # default
    settings.tmp_language = 'Z'
    assert settings.tmp_language == 'Z'


def test_language_history_deduplicates_and_moves_to_front():
    append_to_language_history('A')
    append_to_language_history('B')
    append_to_language_history('C')
    append_to_language_history('A')  # re-selecting A should move it back to front, not duplicate

    assert settings.language_history == ['A', 'C', 'B']


def test_language_history_caps_at_five():
    for code in ['A', 'B', 'C', 'D', 'E', 'F']:
        append_to_language_history(code)

    assert settings.language_history == ['F', 'E', 'D', 'C', 'B']
