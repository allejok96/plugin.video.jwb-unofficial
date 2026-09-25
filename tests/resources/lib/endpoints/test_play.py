import pytest

from resources.lib.jwlib.media import NotFoundError, Media, File, Subtitle
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


def test_wait_for_playback_to_start(kodi):
    kodi.currently_playing_file = 'file.mp4'
    assert play._wait_for_playback_to_start('file.mp4') is True

    # Testing False takes a LOONG time
    # TODO why doesn't it take a LOONG TIME?
    assert play._wait_for_playback_to_start('wrong.mp4') is False


def test_get_subtitles_found(session):
    media = Media.create(
        key='MediaKey', session=session,
        files=[File.create(url='video.mp4', subtitles=Subtitle.create(url='subs.vtt'))],
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
