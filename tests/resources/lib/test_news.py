import pytest

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


@pytest.mark.parametrize('version, expected', [
    ('2.0.0', (2, 0, 0)),
    ('2.10.1', (2, 10, 1)),
    ('10', (10,)),
    ('2.0.0~beta1', (2, 0, 0)),
    ('1.15.3+matrix.1', (1, 15, 3)),
    ('', ()),
    ('unknown', ()),
])
def test_parse_version(version, expected):
    assert news._parse_version(version) == expected


@pytest.mark.parametrize('last_used, news_version, shown', [
    ('', '2.0.0', True),  # upgraded from 1.x
    ('1.15.3', '2.0.0', True),
    ('2.0.0', '2.0.0', False),
    ('2.0.1', '2.0.0', False),
    ('2.9.0', '2.10.0', True),  # would be wrong with string comparison
    ('2.10.0', '2.9.0', False),  # would be wrong with string comparison
    ('9.0.0', '10.0.0', True),  # would be wrong with string comparison
])
def test_show_whats_new_compares_versions_numerically(kodi, monkeypatch, last_used, news_version, shown):
    monkeypatch.setattr(news, 'VERSION', news_version)
    settings.last_used_version = last_used

    news.show_whats_new()

    assert bool(kodi.dialog_messages) is shown
