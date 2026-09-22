import pytest

from resources.lib.endpoints import browse
from resources.lib.jwlib.media import Category, Media
from resources.lib.kodi import ListItem, ItemType
from resources.lib.requests import BrowseRequest


def test_is_unseen_convention(kodi, monkeypatch):
    assert browse.is_unseen_convention('VODStudio') is False

    kodi.user_bool = True # Have you attended? Yes.
    assert browse.is_unseen_convention('ConvReleases') is False

    kodi.user_bool = False  # Have you attended? No.
    assert browse.is_unseen_convention('ConvReleases') is True


def test_merge_category_items(sessions):
    en = sessions.add('E')
    sv = sessions.add('Z')

    en.categories['sub1'] = Category.create(
        key='sub1',
        name='First subcategory',
        session=en,
        type='ondemand'
    )
    sv.categories['sub1'] = Category.create(
        key='sub1',
        name='This category should not be visible',
        session=sv,
        type='ondemand',
    )
    sv.categories['sub2'] = Category.create(
        key='sub2',
        name='Second subcategory',
        session=sv,
        type='ondemand'
    )

    parent_E = Category.create(
        key='parent',
        session=en,
        type='container',
        subcategories=['sub1'],
        media=[Media.create(key='media1', title='First media', session=en)],
    )

    parent_Z = Category.create(
        key='parent',
        session=sv,
        type='container',
        subcategories=['sub2', 'sub1'],
        media=[
            Media.create(key='media2', title='Second media', session=sv),
            Media.create(key='media1', title='This media should not be visible', session=sv),
        ],
    )

    merged = browse.merge_category_items([parent_E, parent_Z])

    assert set(item.title for item in merged) == {
        'First subcategory',
        'Second subcategory',
        'First media',
        'Second media',
    }


def test_sort_items_in_place():
    items = [
        ListItem("1. Middle folder", 'URL1', ItemType.FOLDER, date="2026-01-02"),
        ListItem("2. Oldest video", 'URL2', ItemType.VIDEO, date="2026-01-01"),
        ListItem("3. Oldest folder", 'URL3', ItemType.FOLDER, date="2026-01-01"),
        ListItem("4. Newest folder", 'URL4', ItemType.FOLDER, date="2026-01-03"),
        ListItem("5. Newest video", 'URL5', ItemType.VIDEO, date="2026-01-03"),
        ListItem("6. Middle video", 'URL6', ItemType.VIDEO, date="2026-01-02"),
    ]

    browse.sort_items_in_place(items)

    assert [item.title[3:] for item in items] == [
        "Newest folder",
        "Middle folder",
        "Oldest folder",
        "Newest video",
        "Middle video",
        "Oldest video",
    ]


def test_browse_endpoint(kodi, session):
    session.categories['SubCatKey'] = Category.create(
        key='SubCatKey', name='Some subcategory', session=session, type='ondemand',
    )
    session.categories['CatKey'] = Category.create(
        key='CatKey', name='Some category', session=session, type='container',
        subcategories=['SubCatKey'],
        media=[Media.create(key='MediaKey', title='Some media', session=session)],
    )

    browse.browse_endpoint(BrowseRequest(category='CatKey', hidden=False, media=True))

    assert {item.title for item in kodi.screen_items} == {'Some media', 'Some subcategory'}


@pytest.mark.parametrize('media', [True, False])
def test_browse_endpoint_passes_media_to_session(kodi, session, media):
    session.categories['CatKey'] = Category.create(
        key='CatKey', name='Some category', session=session, type='container', subcategories=[],
    )

    browse.browse_endpoint(BrowseRequest(category='CatKey', hidden=False, media=media))

    assert session.get_category_calls == [('CatKey', media)]


def test_browse_endpoint_convention_not_attended(kodi):
    kodi.user_bool = True  # Have you attended? Yes.
    with pytest.raises(AssertionError):
        # This will try to get the category but fails because we haven't defined any sessions
        browse.browse_endpoint(BrowseRequest(category='ConvReleases', hidden=False, media=False))

    kodi.user_bool = False  # Have you attended? No.
    # This should not even try to get the category, so no failure
    browse.browse_endpoint(BrowseRequest(category='ConvReleases', hidden=False, media=False))
    
    with pytest.raises(AttributeError):
        assert kodi.screen_items
