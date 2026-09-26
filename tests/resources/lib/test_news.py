from resources.lib import news
from resources.lib.settings import settings


def test_show_whats_new_only_once(kodi):
    assert settings.last_used_version == ''  # default, e.g. upgraded from 1.x

    news.show_whats_new()
    news.show_whats_new()

    assert len(kodi.dialog_messages) == 1
    assert settings.last_used_version == kodi.get_addon_version()


def test_show_whats_new_skipped_when_already_shown(kodi):
    news.mark_whats_new_as_shown()

    news.show_whats_new()

    assert kodi.dialog_messages == []
