from resources.lib.endpoints import shuffle
from resources.lib.jwlib.media import Category, Media, File
from resources.lib.jwlib.media.const import MEDIA_AUDIO, MEDIA_VIDEO
from resources.lib.requests import PlayRequest, ShuffleRequest


def test_get_all_media_is_depth_first(session):
    session.categories['Leaf'] = Category.create(
        key='Leaf', name='Leaf', session=session, type='ondemand',
        media=[Media.create(key='LeafMedia', session=session)],
    )
    root = Category.create(
        key='Root', session=session, type='container',
        subcategories=['Leaf'],
        media=[Media.create(key='RootMedia', session=session)],
    )

    media = list(shuffle._get_all_media(root))

    assert [m.key for m in media] == ['LeafMedia', 'RootMedia']


def test_get_unique_media_from_categories_deduplicates(sessions):
    s1 = sessions.add('E')
    cat1 = Category.create(key='Cat1', session=s1, type='ondemand', media=[
        Media.create(key='A', title='First', session=s1),
        Media.create(key='B', title='Second', session=s1),
    ])

    s2 = sessions.add('Z')
    cat2 = Category.create(key='Cat2', session=s2, type='ondemand', media=[
        Media.create(key='A', title='Duplicate of A', session=s2),
        Media.create(key='C', title='Third', session=s2),
    ])

    media = shuffle._get_unique_media_from_categories([cat1, cat2])

    assert [m.key for m in media] == ['A', 'B', 'C']


def test_create_language_agnostic_media_item_no_lang(kodi, session):
    media = Media.create(key='MediaKey', title='Some video', session=session)

    item = shuffle._create_language_agnostic_media_item(media, '')

    assert item.url == PlayRequest(media='MediaKey', hidden=False).url


def test_create_language_agnostic_media_item_audio_with_lang(kodi, session):
    media = Media.create(
        key='MediaKey', title='Some audio', type=MEDIA_AUDIO, session=session,
        files=[File.create(url='audio.mp3')],
    )

    item = shuffle._create_language_agnostic_media_item(media, 'Z')

    assert item.url == media.get_file().url


def test_create_language_agnostic_media_item_video_with_lang(kodi, session):
    media = Media.create(key='MediaKey', title='Some video', type=MEDIA_VIDEO, session=session)

    item = shuffle._create_language_agnostic_media_item(media, 'Z')

    assert item.url == PlayRequest(media='MediaKey', hidden=False, lang='Z', no_redirect=True).url


def test_shuffle_endpoint(kodi, session):
    session.categories['Cat'] = Category.create(key='Cat', name='Cat', session=session, type='ondemand', media=[
        Media.create(key='A', title='First', session=session),
        Media.create(key='B', title='Second', session=session),
    ])

    shuffle.shuffle_endpoint(ShuffleRequest(category='Cat', hidden=False))

    assert {item.title for item in kodi.started_playlist} == {'First', 'Second'}
