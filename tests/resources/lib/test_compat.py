import logging

import pytest

from resources.lib import compat
from resources.lib.compat import migrate_settings
from resources.lib.settings import settings, SubtitleMode


class TestUpgradeVideoRes:
    def test_default_migrates_to_matching_default_resolution(self, kodi, caplog):
        settings.resolution = 1234
        assert kodi.get_setting('video_res') == '0'  # default

        with caplog.at_level(logging.DEBUG):
            compat._upgrade_video_res()

        assert settings.resolution == 1080  # matches the default of video_resolution
        assert caplog.record_tuples == [
            ('resources.lib.compat', logging.INFO, 'Old value: 0'),
            ('resources.lib.compat', logging.INFO, 'New value: 1080'),
        ]

    @pytest.mark.parametrize('old_res, expected', [(1, 720), (2, 480), (3, 360), (4, 240)])
    def test_migrates_known_resolution(self, kodi, old_res, expected):
        kodi.settings['video_res'] = str(old_res)

        compat._upgrade_video_res()

        assert settings.resolution == expected

    def test_unknown_resolution_raises(self, kodi):
        settings.resolution = 1234
        kodi.settings['video_res'] = '5'  # not in the mapping

        with pytest.raises(KeyError):
            compat._upgrade_video_res()

        assert settings.resolution == 1234  # untouched


class TestUpgradeRememberLang:
    def test_default_disables_original_audio(self, kodi):
        settings.set_second_language('S', 'Spanish')
        settings.original_audio = True
        assert kodi.get_setting('remember_lang') == 'false'  # default

        compat._upgrade_remember_lang()

        assert settings.second_language == 'S'  # unchanged
        assert settings.original_audio is False

    def test_disables_original_audio_when_tmp_language_matches_current_language(self, kodi):
        kodi.settings['remember_lang'] = 'true'
        settings.set_language('Z', 'Swedish')
        settings.set_second_language('S', 'Spanish')
        settings.tmp_language = 'Z'

        compat._upgrade_remember_lang()

        assert settings.second_language == 'S'  # unchanged
        assert settings.original_audio is False

    def test_migrates_when_remember_lang_was_active_and_language_differs(self, kodi, sessions):
        sessions.add('D').add_common_languages()

        kodi.settings['remember_lang'] = 'true'
        settings.set_language('D', 'German / Deutsch')
        settings.tmp_language = 'Z'
        settings.original_audio = False

        compat._upgrade_remember_lang()

        assert settings.second_language == 'Z'
        assert kodi.get_setting('second_language_name') == 'Swedish / Svenska'
        assert settings.original_audio is True

    def test_migrates_with_fallback_label_when_language_lookup_fails(self, kodi, sessions):
        sessions.add('E').add_common_languages()

        kodi.settings['remember_lang'] = 'true'
        settings.set_language('E', 'English')
        settings.tmp_language = 'X'

        compat._upgrade_remember_lang()

        assert settings.second_language == 'X'
        assert kodi.get_setting('second_language_name') == 'X'  # falls back to the raw code
        assert settings.original_audio is True


class TestUpgradeSubtitles:
    def test_default_is_noop(self, kodi):
        assert settings.subtitle_mode == SubtitleMode.ORIG_AND_FOREIGN  # default
        assert kodi.get_setting('subtitles') == 'false'  # default

        compat._upgrade_subtitles()

        assert settings.subtitle_mode == SubtitleMode.ORIG_AND_FOREIGN  # unchanged

    def test_migrates_when_active(self, kodi):
        kodi.settings['subtitles'] = 'true'

        compat._upgrade_subtitles()

        assert settings.subtitle_mode == SubtitleMode.ON


class TestLastVersion:
    def test_roundtrip(self, kodi):
        compat._set_last_version(5)

        assert kodi.get_setting('last_settings_version') == '5'
        assert compat._get_last_version() == 5


class TestMigrateSettings:
    def test_fresh_install_runs_all_routines_in_order_and_bumps_version(self, kodi, monkeypatch):
        calls = []
        monkeypatch.setattr(compat, '_upgrade_routines', [
            (lambda: calls.append(0), 'zero'),
            (lambda: calls.append(1), 'one'),
            (lambda: calls.append(2), 'two'),
        ])
        assert kodi.get_setting('last_settings_version') == '0'  # default

        result = migrate_settings()

        assert calls == [0, 1, 2]
        assert kodi.get_setting('last_settings_version') == '3'
        assert result is True

    def test_only_runs_routines_after_last_migrated_version(self, kodi, monkeypatch):
        calls = []
        monkeypatch.setattr(compat, '_upgrade_routines', [
            (lambda: calls.append(0), 'zero'),
            (lambda: calls.append(1), 'one'),
            (lambda: calls.append(2), 'two'),
        ])
        kodi.settings['last_settings_version'] = '1'

        result = migrate_settings()

        assert calls == [1, 2]
        assert kodi.get_setting('last_settings_version') == '3'
        assert result is True

    def test_skips_entirely_when_already_up_to_date(self, kodi, monkeypatch):
        calls = []
        monkeypatch.setattr(compat, '_upgrade_routines', [
            (lambda: calls.append(0), 'zero'),
        ])
        kodi.settings['last_settings_version'] = '1'

        result = migrate_settings()

        assert calls == []
        assert kodi.get_setting('last_settings_version') == '1'  # left untouched
        assert result is True

    def test_failed_routine_is_logged_but_version_still_bumped(self, kodi, monkeypatch, caplog):
        # Migration is only ever attempted once - a failed routine is logged and reported to the
        # caller (so it can notify the user), but is not retried on the next run.
        calls = []
        monkeypatch.setattr(compat, '_upgrade_routines', [
            (lambda: (_ for _ in ()).throw(RuntimeError('kaboom')), 'boom'),
            (lambda: calls.append(1), 'one'),
        ])

        with caplog.at_level(logging.DEBUG):
            result = migrate_settings()

        assert calls == [1]  # later routines still run
        assert kodi.get_setting('last_settings_version') == '2'
        assert result is False
        assert ('resources.lib.compat', logging.INFO, 'boom - failed') in caplog.record_tuples

    def test_failure_to_read_version_is_treated_as_a_failed_migration(self, kodi, monkeypatch, caplog):
        monkeypatch.setattr(compat, '_get_last_version', lambda: (_ for _ in ()).throw(ValueError))

        with caplog.at_level(logging.DEBUG):
            result = migrate_settings()

        assert result is False
        assert kodi.get_setting('last_settings_version') == str(len(compat._upgrade_routines))
