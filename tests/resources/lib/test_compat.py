import pytest

from resources.lib import compat
from resources.lib.compat import migrate_settings
from resources.lib.kodi import LogLevel
from resources.lib.settings import settings, SubtitleMode


class TestUpgradeVideoRes:
    def test_default_is_noop(self, kodi):
        settings.resolution = 1234
        assert kodi.get_setting('video_res') == '0'  # default

        compat._upgrade_video_res()

        assert settings.resolution == 1234  # unchanged
        assert kodi.logged_messages == []

    @pytest.mark.parametrize('old_res, expected', [(1, 720), (2, 480), (3, 360), (4, 240)])
    def test_migrates_known_resolution(self, kodi, old_res, expected):
        kodi.settings['video_res'] = str(old_res)

        compat._upgrade_video_res()

        assert settings.resolution == expected
        assert kodi.logged_messages == [(LogLevel.INFO, 'Migrating legacy video resolution setting')]

    def test_unknown_resolution_logs_failure_and_leaves_setting_untouched(self, kodi):
        settings.resolution = 1234
        kodi.settings['video_res'] = '5'  # not in RES_ENUM

        compat._upgrade_video_res()

        assert settings.resolution == 1234  # untouched
        assert kodi.logged_messages == [
            (LogLevel.INFO, 'Migrating legacy video resolution setting'),
            (LogLevel.INFO, 'Failed to migrate video resolution setting'),
        ]


class TestUpgradeRememberLang:
    def test_default_is_noop(self, kodi):
        settings.set_second_language('S', 'Spanish')
        settings.original_audio = True
        assert kodi.get_setting('remember_lang') == 'false'  # default

        compat._upgrade_remember_lang()

        assert settings.second_language == 'S'  # unchanged
        assert settings.original_audio is True
        assert kodi.logged_messages == []

    def test_noop_when_tmp_language_matches_current_language(self, kodi):
        kodi.settings['remember_lang'] = 'true'
        settings.set_language('Z', 'Swedish')
        settings.set_second_language('S', 'Spanish')
        settings.tmp_language = 'Z'
        kodi.logged_messages.clear()  # discard log noise from set_language() above

        compat._upgrade_remember_lang()

        assert settings.second_language == 'S'  # unchanged
        assert settings.original_audio is False
        assert kodi.logged_messages == []

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
        assert settings.subtitle_mode == SubtitleMode.ORIG_AND_FOREIGN # default
        assert kodi.get_setting('subtitles') == 'false'  # default

        compat._upgrade_subtitles()

        assert settings.subtitle_mode == SubtitleMode.ORIG_AND_FOREIGN  # unchanged
        assert kodi.logged_messages == []

    def test_migrates_when_active(self, kodi):
        kodi.settings['subtitles'] = 'true'

        compat._upgrade_subtitles()

        assert settings.subtitle_mode == SubtitleMode.ON
        assert kodi.logged_messages == [(LogLevel.INFO, 'Migrating legacy subtitle setting')]


class TestLastVersion:
    def test_roundtrip(self, kodi):
        compat._set_last_version(5)

        assert kodi.get_setting('last_settings_version') == '5'
        assert compat._get_last_version() == 5


class TestMigrateSettings:
    def test_fresh_install_runs_all_routines_in_order_and_bumps_version(self, kodi, monkeypatch):
        calls = []
        monkeypatch.setattr(compat, '_upgrade_routines', [
            lambda: calls.append(0),
            lambda: calls.append(1),
            lambda: calls.append(2),
        ])
        assert kodi.get_setting('last_settings_version') == '0'  # default

        migrate_settings()

        assert calls == [0, 1, 2]
        assert kodi.get_setting('last_settings_version') == '3'

    def test_only_runs_routines_after_last_migrated_version(self, kodi, monkeypatch):
        calls = []
        monkeypatch.setattr(compat, '_upgrade_routines', [
            lambda: calls.append(0),
            lambda: calls.append(1),
            lambda: calls.append(2),
        ])
        kodi.settings['last_settings_version'] = '1'

        migrate_settings()

        assert calls == [1, 2]
        assert kodi.get_setting('last_settings_version') == '3'

    def test_skips_entirely_when_already_up_to_date(self, kodi, monkeypatch):
        calls = []
        monkeypatch.setattr(compat, '_upgrade_routines', [
            lambda: calls.append(0)
        ])
        kodi.settings['last_settings_version'] = '1'

        migrate_settings()

        assert calls == []
        assert kodi.get_setting('last_settings_version') == '1'  # left untouched

    def test_version_is_not_bumped_after_a_failed_routine(self, kodi, monkeypatch):
        # So that a failed migration is retried on the next run.
        monkeypatch.setattr(compat, '_upgrade_routines', [
            lambda: (_ for _ in ()).throw(RuntimeError('kaboom')),
            lambda: None,
        ])

        with pytest.raises(RuntimeError):
            migrate_settings()

        assert kodi.get_setting('last_settings_version') == '0'  # unchanged
