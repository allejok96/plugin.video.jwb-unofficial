import pytest

from resources.lib import jwgui
from resources.lib.jwlib.media import Category, Media
from resources.lib.jwlib.media.const import CATEGORY_CONTAINER, CATEGORY_ONDEMAND, MEDIA_AUDIO, MEDIA_VIDEO, \
    TAG_EXCLUDE_APPLETV
from resources.lib.jwlib.search import Result
from resources.lib.jwlib.search.const import TYPE_AUDIO, TYPE_VIDEO, TYPE_VIDEO_CAT
from resources.lib.kodi import ItemType
from resources.lib.requests import BrowseRequest, LanguageRequest, PlayRequest, ShuffleRequest


def test_create_category_item(session):
    cat = Category.create(key='A', name='Category A', session=session, type='container')

    item = jwgui.create_category_item(cat, fanart='FANART')

    assert item.title == 'Category A'
    assert item.fanart == 'FANART'
    assert item.type == ItemType.FOLDER
    assert item.url == BrowseRequest(category='A', hidden=False, media=False).url
    assert item.menu == [
        ('STRING #30401', ShuffleRequest(category='A', hidden=False).url),
        ('STRING #30402', LanguageRequest(shuffle_category='A', hidden=False).url),
    ]


def test_create_category_item_hidden(session):
    cat = Category.create(key='A', name='Category A', session=session, type='container', tags=[TAG_EXCLUDE_APPLETV])

    item = jwgui.create_category_item(cat)

    assert item.url == BrowseRequest(category='A', hidden=True, media=False).url


@pytest.mark.parametrize('cat_type, expected', [(CATEGORY_ONDEMAND, True), (CATEGORY_CONTAINER, False)])
def test_has_media(session, cat_type, expected):
    cat = Category.create(key='A', name='Category A', session=session, type=cat_type)

    assert jwgui._has_media(cat) is expected


@pytest.mark.parametrize('cat_type, expected_media', [(CATEGORY_ONDEMAND, True), (CATEGORY_CONTAINER, False)])
def test_create_category_item_sets_media_from_category_type(session, cat_type, expected_media):
    cat = Category.create(key='A', name='Category A', session=session, type=cat_type)

    item = jwgui.create_category_item(cat)

    assert item.url == BrowseRequest(category='A', hidden=False, media=expected_media).url


def test_create_media_item_video(session):
    media = Media.create(key='A', title='Media A', type=MEDIA_VIDEO, session=session)

    item = jwgui.create_media_item(media)

    assert item.title == 'Media A'
    assert item.type == ItemType.VIDEO
    assert item.url == PlayRequest(media='A', hidden=False).url
    assert item.menu == [('STRING #30400', LanguageRequest(play_media='A', hidden=False).url)]


def test_create_media_item_audio(session):
    media = Media.create(key='A', title='Media A', type=MEDIA_AUDIO, session=session)

    item = jwgui.create_media_item(media)

    assert item.type == ItemType.AUDIO


def test_create_media_item_custom_language_and_no_redirect(session):
    media = Media.create(key='A', title='Media A', session=session)

    item = jwgui.create_media_item(media, language='Z', no_redirect=True)

    assert item.url == PlayRequest(media='A', hidden=False, lang='Z', no_redirect=True).url


def test_create_media_item_with_url_overrides(session):
    media = Media.create(key='A', title='Media A', session=session)

    item = jwgui.create_media_item_with_url(media, url='https://example.org/direct.mp4')

    assert item.url == 'https://example.org/direct.mp4'


def test_create_search_result_category():
    result = Result({
        'subtype': TYPE_VIDEO_CAT, 'lank': 'mc-VODChildren', 'title': 'Children',
        'image': {'url': 'IMG'},
    })

    item = jwgui.create_search_result(result)

    assert item.type == ItemType.FOLDER
    assert item.title == 'Children'
    assert item.icon == 'IMG'
    assert item.url == BrowseRequest(category='VODChildren', hidden=False, media=False).url


def test_create_search_result_video():
    result = Result({
        'subtype': TYPE_VIDEO, 'lank': 'MediaKey', 'title': 'Some video',
        'snippet': 'plain <strong>bold</strong> text', 'duration': '1:02:03',
    })

    item = jwgui.create_search_result(result)

    assert item.type == ItemType.VIDEO
    assert item.description == 'plain [B]bold[/B] text'
    assert item.duration == 3723
    assert item.url == PlayRequest(media='MediaKey', hidden=False).url
    assert item.menu == [('STRING #30400', LanguageRequest(play_media='MediaKey', hidden=False).url)]


def test_create_search_result_audio():
    result = Result({'subtype': TYPE_AUDIO, 'lank': 'MediaKey', 'title': 'Some audio', 'snippet': 'text'})

    item = jwgui.create_search_result(result)

    assert item.type == ItemType.AUDIO


def test_create_search_result_uses_deep_links():
    result = Result({
        'subtype': TYPE_VIDEO, 'lank': 'MediaKey', 'title': 'Some video', 'snippet': 'ignored',
        'deepLinks': [{'jumpLabel': 'Jump to 1:00', 'snippet': 'first clip'}],
    })

    item = jwgui.create_search_result(result)

    assert item.description == 'Jump to 1:00\nfirst clip'


def test_show_disclaimer(kodi):
    jwgui.show_disclaimer()

    assert kodi.dialog_messages == ['STRING #30310: STRING #30311']
