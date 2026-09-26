import logging

import pytest

from resources.lib.jwlib.media import NotFoundError, Media, File, Subtitles
from resources.lib.endpoints import play
from resources.lib.requests import PlayRequest
from resources.lib.settings import settings, SubtitleMode


def test_get_title_language():
    settings.set_language('DEFAULT', 'Default')
    settings.set_second_language('SECOND', 'Second')

    settings.enable_fallback = False
    settings.original_audio = False
    assert play._get_title_language('') == ['DEFAULT', 'DEFAULT']

    settings.enable_fallback = False
    settings.original_audio = True
    assert play._get_title_language('') == ['DEFAULT', 'DEFAULT']

    settings.enable_fallback = True
    settings.original_audio = False
    assert play._get_title_language('') == ['DEFAULT', 'SECOND']

    settings.enable_fallback = True
    settings.original_audio = True
    assert play._get_title_language('') == ['DEFAULT', 'SECOND']


def test_get_title_and_playback_language_explicit():
    settings.set_language('DEFAULT', 'Default')
    settings.set_second_language('SECOND', 'Second')

    for fallback in (False, True):
        for original in (False, True):
            settings.enable_fallback = fallback
            settings.original_audio = original
            assert play._get_title_language('EXPLICIT') == ['EXPLICIT']
            assert play._get_playback_language('EXPLICIT', is_video=True) == ['EXPLICIT']
            assert play._get_playback_language('EXPLICIT', is_video=False) == ['EXPLICIT']


def test_get_video_playback_language():
    settings.set_language('DEFAULT', 'Default')
    settings.set_second_language('SECOND', 'Second')

    settings.enable_fallback = False
    settings.original_audio = False
    assert play._get_playback_language('', is_video=True) == ['DEFAULT', 'DEFAULT', 'DEFAULT']

    settings.enable_fallback = True
    settings.original_audio = False
    assert play._get_playback_language('', is_video=True) == ['DEFAULT', 'DEFAULT', 'SECOND']

    settings.enable_fallback = False
    settings.original_audio = True
    assert play._get_playback_language('', is_video=True) == ['SECOND', 'DEFAULT', 'DEFAULT']

    settings.enable_fallback = True
    settings.original_audio = True
    assert play._get_playback_language('', is_video=True) == ['SECOND', 'DEFAULT', 'SECOND']


def test_get_audio_playback_language():
    settings.set_language('DEFAULT', 'Default')
    settings.set_second_language('SECOND', 'Second')

    settings.enable_fallback = False
    settings.original_audio = False
    assert play._get_playback_language('', is_video=False) == ['DEFAULT', 'DEFAULT']

    settings.enable_fallback = False
    settings.original_audio = True
    assert play._get_playback_language('', is_video=False) == ['DEFAULT', 'DEFAULT']

    settings.enable_fallback = True
    settings.original_audio = False
    assert play._get_playback_language('', is_video=False) == ['DEFAULT', 'SECOND']

    settings.enable_fallback = True
    settings.original_audio = True
    assert play._get_playback_language('', is_video=False) == ['DEFAULT', 'SECOND']


def test_get_media_duplicate_languages_ignored(session):
    session.media = {'MediaKey': Media.create(key='MediaKey', session=session)}

    cache = play._MultiLangMediaCache(key='MediaKey', hidden=False)
    cache.get(['E', 'E'])
    cache.get(['E'])

    assert session.get_media_calls == ['MediaKey']


def test_get_media_duplicate_fails_ignored(session):
    session.missing_media.add('InvalidMedia')

    cache = play._MultiLangMediaCache(key='InvalidMedia', hidden=False)

    with pytest.raises(NotFoundError):
        cache.get(['E', 'E'])

    with pytest.raises(NotFoundError):
        cache.get(['E'])

    assert session.get_media_calls == ['InvalidMedia']


def test_get_subtitle_visibility_off(kodi):
    settings.subtitle_mode = SubtitleMode.OFF
    assert play._get_subtitle_visibility('E') is False
    assert play._get_subtitle_visibility('Z') is False


def test_get_subtitle_visibility_on(kodi):
    settings.subtitle_mode = SubtitleMode.ON
    assert play._get_subtitle_visibility('E') is True
    assert play._get_subtitle_visibility('Z') is True


def test_get_subtitle_visibility_orig_and_foreign(kodi):
    settings.subtitle_mode = SubtitleMode.ORIG_AND_FOREIGN
    settings.set_language('E', 'English')
    assert play._get_subtitle_visibility('E') is False
    assert play._get_subtitle_visibility('Z') is True


def test_get_subtitle_visibility_foreign(kodi):
    settings.subtitle_mode = SubtitleMode.FOREIGN
    settings.set_language('Z', 'Swedish')
    settings.set_second_language('E', 'English')
    settings.original_audio = True

    assert play._get_subtitle_visibility('Z') is False  # own language
    assert play._get_subtitle_visibility('E') is False  # original audio language
    assert play._get_subtitle_visibility('F') is True  # a foreign language


@pytest.fixture
def sleeps(monkeypatch):
    """Record calls to time.sleep() in play.py, without actually sleeping"""
    calls = []
    monkeypatch.setattr(play.time, 'sleep', calls.append)
    return calls


def test_wait_for_playback_to_start(kodi, sleeps):
    kodi.currently_playing_file = 'file.mp4'
    assert play._wait_for_playback_to_start('file.mp4') is True
    assert sleeps == []


def test_wait_for_playback_to_start_gives_up_on_wrong_file(kodi, sleeps):
    kodi.currently_playing_file = 'wrong.mp4'
    assert play._wait_for_playback_to_start('file.mp4') is False
    assert len(sleeps) == 20


def test_wait_for_playback_to_start_gives_up_when_nothing_plays(kodi, sleeps):
    assert play._wait_for_playback_to_start('file.mp4') is False
    assert len(sleeps) == 20


def test_wait_for_playback_to_start_retries_until_playing(kodi, sleeps, monkeypatch):
    # Previous file keeps playing for a few seconds before our file starts
    monkeypatch.setattr(kodi, 'get_playing_file', lambda: 'file.mp4' if len(sleeps) >= 3 else 'previous.mp4')
    assert play._wait_for_playback_to_start('file.mp4') is True
    assert len(sleeps) == 3


def test_get_subtitles_found(session):
    media = Media.create(
        key='MediaKey', session=session,
        files=[File.create(url='video.mp4', subtitles=Subtitles.create(url='subs.vtt'))],
    )
    session.media['MediaKey'] = media

    assert play._get_subtitles(play._MultiLangMediaCache('MediaKey', hidden=False)) == ['subs.vtt']


def test_get_subtitles_none_available(session):
    media = Media.create(key='MediaKey', session=session, files=[File.create(url='video.mp4')])
    session.media['MediaKey'] = media

    assert play._get_subtitles(play._MultiLangMediaCache('MediaKey', hidden=False)) == []


def test_get_subtitles_not_found(session):
    session.missing_media.add('MediaKey')

    assert play._get_subtitles(play._MultiLangMediaCache('MediaKey', hidden=False)) == []


def test_play_media(kodi, session):
    media = Media.create(
        key='MediaKey', title='Some video', session=session,
        files=[File.create(url='video.mp4')],
    )
    session.media['MediaKey'] = media

    play._play_media('MediaKey', request_lang='', hidden=False)
    assert kodi.resolved.url == 'video.mp4'


@pytest.mark.parametrize('mode, visible', [(SubtitleMode.ON, True), (SubtitleMode.OFF, False)])
def test_play_media_sets_subtitle_visibility_without_external_subtitles(kodi, session, mode, visible):
    # Files may have hardcoded subtitles, so visibility must be set even without external subtitles
    settings.subtitle_mode = mode
    session.media['MediaKey'] = Media.create(key='MediaKey', session=session, files=[File.create(url='video.mp4')])

    play._play_media('MediaKey', request_lang='', hidden=False)

    assert kodi.subtitle_visibility is visible


def test_play_media_skips_subtitle_visibility_when_playback_never_starts(kodi, session, sleeps, monkeypatch, caplog):
    session.media['MediaKey'] = Media.create(key='MediaKey', session=session, files=[File.create(url='video.mp4')])
    monkeypatch.setattr(kodi, 'get_playing_file', lambda: 'something_else.mp4')
    monkeypatch.setattr(kodi, 'show_subtitles', lambda show: pytest.fail('show_subtitles() should not be called'))

    play._play_media('MediaKey', request_lang='', hidden=False)

    assert ('resources.lib.endpoints.play', logging.WARNING,
            'Not setting subtitle visibility, because playback never started') in caplog.record_tuples


def test_play_endpoint_redirects_with_lang(kodi):
    request = PlayRequest(media='MediaKey', hidden=False, lang='Z')

    play.play_endpoint(request)

    assert settings.tmp_language == 'Z'
    assert kodi.executed_commands == ['PlayMedia(' + PlayRequest(media='MediaKey', hidden=False).url + ', resume)']


def test_play_endpoint_plays_directly_when_hidden(kodi, sessions):
    # This session is used for subtitles in default language
    en = sessions.add('E', hidden=True)
    en.media['MediaKey'] = Media.create(key='MediaKey', title='English', session=en, files=[File.create(url='en.mp4')])

    # This session is for Play in another language
    sv = sessions.add('Z', hidden=True)
    sv.media['MediaKey'] = Media.create(key='MediaKey', title='Swedish', session=sv, files=[File.create(url='sv.mp4')])

    request = PlayRequest(media='MediaKey', hidden=True, lang='Z')

    play.play_endpoint(request)

    assert settings.tmp_language == ''
    assert kodi.resolved.title == 'Swedish'


def test_play_endpoint_plays_directly_when_no_redirect(kodi, sessions):
    # This session is used for subtitles in default language
    en = sessions.add('E')
    en.media['MediaKey'] = Media.create(key='MediaKey', title='English', session=en, files=[File.create(url='en.mp4')])

    # This session is for Play in another language
    sv = sessions.add('Z')
    sv.media['MediaKey'] = Media.create(key='MediaKey', title='Swedish', session=sv, files=[File.create(url='sv.mp4')])

    request = PlayRequest(media='MediaKey', hidden=False, lang='Z', no_redirect=True)

    play.play_endpoint(request)

    assert settings.tmp_language == ''
    assert kodi.resolved.title == 'Swedish'


def test_play_endpoint_uses_and_resets_tmp_language(kodi, sessions):
    # After a redirect, the language is carried over in tmp_language
    en = sessions.add('E')
    en.media['MediaKey'] = Media.create(key='MediaKey', title='English', session=en, files=[File.create(url='en.mp4')])
    sv = sessions.add('Z')
    sv.media['MediaKey'] = Media.create(key='MediaKey', title='Swedish', session=sv, files=[File.create(url='sv.mp4')])
    settings.tmp_language = 'Z'

    play.play_endpoint(PlayRequest(media='MediaKey', hidden=False))

    assert settings.tmp_language == ''
    assert kodi.resolved.title == 'Swedish'
