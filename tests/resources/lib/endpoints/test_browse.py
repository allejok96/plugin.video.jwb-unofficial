import pytest

from resources.lib.endpoints import browse
from resources.lib.jwlib.media import Category, Media
from resources.lib.requests import BrowseRequest


def test_is_unseen_convention(kodi, monkeypatch):
    assert browse._is_unseen_convention('VODStudio') is False

    kodi.user_bool = True # Have you attended? Yes.
    assert browse._is_unseen_convention('ConvReleases') is False

    kodi.user_bool = False  # Have you attended? No.
    assert browse._is_unseen_convention('ConvReleases') is True


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

    assert [item.title for item in kodi.screen_items] == ['Some subcategory', 'Some media']


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
