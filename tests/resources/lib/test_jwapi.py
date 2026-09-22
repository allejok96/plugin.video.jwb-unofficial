import pytest

from resources.lib import jwapi
from resources.lib.jwlib.media import NotFoundError, Media, File, Category
from resources.lib.jwlib.media.const import CLIENT_APPLETV, CLIENT_NONE, TAG_EXCLUDE_APPLETV
from resources.lib.settings import settings, SubtitleMode


# _get_session

def test_get_session_uses_given_language(kodi, sessions):
    sessions.add('Z')
    session = jwapi.get_session('Z', hidden=False)
    assert session.language == 'Z'
    assert session.client_type == CLIENT_APPLETV


def test_get_session_falls_back_to_settings_language(kodi, sessions):
    kodi.settings['language'] = 'F'
    sessions.add('F')
    session = jwapi.get_session(hidden=False)
    assert session.language == 'F'


def test_get_session_hidden_uses_none_client(kodi, sessions):
    sessions.add('E', hidden=True)
    session = jwapi.get_session('E', hidden=True)
    assert session.client_type == CLIENT_NONE


# get_best_url

def test_get_best_url_prefers_highest_within_resolution_limit(kodi, session):
    settings.resolution = 720
    media = Media.create(
        files=[
            File.create(resolution=240, url='240.mp4'),
            File.create(resolution=720, url='720.mp4'),
            File.create(resolution=1080, url='1080.mp4'),
            File.create(resolution=480, url='480.mp4'),
        ],
        session=session,
    )

    assert jwapi.get_best_url(media) == '720.mp4'


def test_get_best_url_avoids_hardsubs_by_default(kodi, session):
    media = Media.create(
        files=[
            File.create(resolution=480, url='480.mp4', subtitled_hard=False),
            File.create(resolution=720, url='720.mp4', subtitled_hard=True),
        ],
        session=session,
    )
    assert jwapi.get_best_url(media) == '480.mp4'


def test_get_best_url_prefers_subtitled_when_mode_on(kodi, session):
    settings.subtitle_mode = SubtitleMode.ON
    media = Media.create(
        files=[
            File.create(resolution=480, url='480.mp4', subtitled_hard=False),
            File.create(resolution=720, url='720.mp4', subtitled_hard=True),
        ],
        session=session,
    )

    assert jwapi.get_best_url(media) == '720.mp4'


# is_hidden / is_convention_release_root

def test_is_hidden_category_with_exclude_tag(session):
    cat = Category.create(key='cat', session=session, type='container', tags=[TAG_EXCLUDE_APPLETV])
    assert jwapi.is_hidden(cat) is True


def test_is_hidden_category_without_tag(session):
    cat = Category.create(key='cat', session=session, type='container')
    assert jwapi.is_hidden(cat) is False


def test_is_hidden_convention_release_root_is_never_hidden(session):
    cat = Category.create(key='ConvReleases', session=session, type='container', tags=[TAG_EXCLUDE_APPLETV])
    assert jwapi.is_hidden(cat) is False


def test_is_hidden_media(session):
    media = Media.create(tags=[TAG_EXCLUDE_APPLETV], session=session)
    assert jwapi.is_hidden(media) is True


def test_is_convention_release_root():
    assert jwapi.is_convention_release_root('ConvReleases') is True
    assert jwapi.is_convention_release_root('VODStudio') is False


# get_media

def test_get_media_falls_back_through_languages(sessions):
    en = sessions.add('E')
    en.missing_media.add('media')

    sv = sessions.add('Z')
    media = Media.create(session=sv)
    sv.media = {'media': media}

    assert jwapi.get_media('media', languages=['E', 'Z'], hidden=False) is media


def test_get_media_raises_when_not_found_anywhere(sessions):
    sessions.add('E').missing_media.add('media')
    sessions.add('Z').missing_media.add('media')
    with pytest.raises(NotFoundError):
        jwapi.get_media('media', languages=['E', 'Z'], hidden=False)


def test_get_media_skips_empty_language_strings(session):
    media = Media.create(session=session)
    session.media['media'] = media

    assert jwapi.get_media('media', languages=['', 'E'], hidden=False) is media
    assert len(session.get_media_calls) == 1


# get_category_multilanguage

def test_get_category_multilanguage_returns_categories_found(sessions):
    en = sessions.add('E')
    cat1 = Category.create(key='cat', session=en, type='ondemand')
    en.categories['cat'] = cat1

    sv = sessions.add('Z')
    cat2 = Category.create(key='cat', session=sv, type='ondemand')
    sv.categories['cat'] = cat2

    cats = jwapi.get_category_multilanguage('cat', languages=['E', 'Z'], hidden=False, include_media=False)
    assert cats == [cat1, cat2]


def test_get_category_multilanguage_skips_missing_languages(sessions):
    en = sessions.add('E')
    en.missing_categories.add('cat')

    sv = sessions.add('Z')
    cat2 = Category.create(key='cat', session=sv, type='ondemand')
    sv.categories['cat'] = cat2

    cats = jwapi.get_category_multilanguage('cat', languages=['E', 'Z'], hidden=False, include_media=False)
    assert cats == [cat2]


def test_get_category_multilanguage_raises_when_none_found(sessions):
    en = sessions.add('E')
    en.missing_categories.add('cat')

    sv = sessions.add('Z')
    sv.missing_categories.add('cat')

    with pytest.raises(NotFoundError):
        jwapi.get_category_multilanguage('cat', languages=['E', 'Z'], hidden=False, include_media=False)


def test_get_category_multilanguage_deduplicates_languages(session, monkeypatch):
    cat = Category.create(key='cat', session=session, type='ondemand')
    session.categories['cat'] = cat

    cats = jwapi.get_category_multilanguage('cat', languages=['E', 'E'], hidden=False, include_media=False)

    assert cats == [cat]
    assert session.get_category_calls == [('cat', False)]
