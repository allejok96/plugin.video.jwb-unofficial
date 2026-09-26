import pytest

import resources.lib.endpoints.search as search
from resources.lib.jwlib.search import ResultPage
from resources.lib.jwlib.search.const import FILTER_AUDIO, FILTER_VIDEO
from resources.lib.kodi import ItemType
from resources.lib.requests import SearchRequest
from resources.lib.settings import settings


def make_result_page(*, filter_type=FILTER_VIDEO, page=1, results=None, next_link=None, token='TOKEN'):
    data = {
        'insight': {'filter': filter_type, 'page': page, 'offset': 0, 'query': 'test'},
        'results': results or [],
    }
    if next_link:
        data['pagination'] = {'links': [{'type': 'next', 'link': next_link, 'label': 'Next'}]}

    return ResultPage(data, token=token)


def test_create_audio_button(kodi):
    item = search._create_audio_button('cats')

    assert item.type == ItemType.FOLDER
    assert item.url == SearchRequest(q='cats', audio=True).url


def test_create_next_button(kodi):
    item = search._create_next_button('https://example.org/next')

    assert item.type == ItemType.FOLDER
    assert item.url == SearchRequest(page='https://example.org/next').url


def test_get_result_from_query(kodi, monkeypatch):
    page = make_result_page()
    captured = {}

    def fake_search(query, *, filter_type, language, token):
        captured['args'] = (query, filter_type, language, token)
        return page

    monkeypatch.setattr(search, 'search', fake_search)
    settings.token = 'STORED_TOKEN'

    result = search._get_result_from_query('cats', audio=True)

    assert result is page
    assert captured['args'] == ('cats', FILTER_AUDIO, settings.language, 'STORED_TOKEN')


def test_get_result_from_url(kodi, monkeypatch):
    page = make_result_page()
    captured = {}

    def fake_from_url(url, token=''):
        captured['args'] = (url, token)
        return page

    monkeypatch.setattr(ResultPage, 'from_url', staticmethod(fake_from_url))
    settings.token = 'STORED_TOKEN'

    result = search._get_result_from_url('https://example.org/page2')

    assert result is page
    assert captured['args'] == ('https://example.org/page2', 'STORED_TOKEN')


def test_is_first_page_of_videos_true():
    page = make_result_page(filter_type=FILTER_VIDEO, page=1)
    assert search._is_first_page_of_videos(page) is True


def test_is_first_page_of_videos_false_when_audio():
    page = make_result_page(filter_type=FILTER_AUDIO, page=1)
    assert search._is_first_page_of_videos(page) is False


def test_is_first_page_of_videos_false_when_not_first_page():
    page = make_result_page(filter_type=FILTER_VIDEO, page=2)
    assert search._is_first_page_of_videos(page) is False


def test_build_screen_first_page_shows_audio_button(kodi):
    page = make_result_page(filter_type=FILTER_VIDEO, page=1)

    search._build_screen(page)

    assert settings.token == 'TOKEN'
    assert kodi.screen_items[0].url == SearchRequest(q='test', audio=True).url


def test_build_screen_second_page_hides_audio_button(kodi):
    page = make_result_page(filter_type=FILTER_VIDEO, page=2)

    search._build_screen(page)

    assert kodi.screen_items == []


def test_build_screen_includes_next_button(kodi):
    page = make_result_page(filter_type=FILTER_AUDIO, page=1, next_link='https://example.org/next')

    search._build_screen(page)

    assert kodi.screen_items[-1].url == SearchRequest(page='https://example.org/next').url


def test_search_endpoint_with_query(kodi, monkeypatch):
    page = make_result_page()
    captured = {}

    def fake_get_result_from_query(q, audio):
        captured['args'] = (q, audio)
        return page

    def fail_input_dialog():
        raise AssertionError('Search box should not be shown when query is given')

    monkeypatch.setattr(search, '_get_result_from_query', fake_get_result_from_query)
    monkeypatch.setattr(kodi, 'input_dialog', fail_input_dialog)

    search.search_endpoint(SearchRequest(q='cats', audio=True))

    assert kodi.screen_items
    assert captured['args'] == ('cats', True)


def test_search_endpoint_with_page(kodi, monkeypatch):
    page = make_result_page()
    captured = {}

    def fake_get_result_from_url(url):
        captured['url'] = url
        return page

    monkeypatch.setattr(search, '_get_result_from_url', fake_get_result_from_url)

    request = SearchRequest(page='https://example.org/next')
    search.search_endpoint(request)

    assert kodi.screen_items
    assert captured['url'] == request.page


@pytest.mark.parametrize('audio', [False, True])
def test_search_endpoint_shows_search_box(kodi, monkeypatch, audio):
    page = make_result_page()
    captured = {}

    def fake_get_result_from_query(q, audio):
        captured['args'] = (q, audio)
        return page

    monkeypatch.setattr(search, '_get_result_from_query', fake_get_result_from_query)
    kodi.user_string = 'dogs'

    search.search_endpoint(SearchRequest(audio=audio))

    assert kodi.screen_items
    assert captured['args'] == ('dogs', audio)


def test_search_endpoint_search_box_cancelled(kodi, monkeypatch):
    def fail_get_result_from_query(q, audio):
        raise AssertionError('Should not search when user cancels')

    monkeypatch.setattr(search, '_get_result_from_query', fail_get_result_from_query)
    kodi.user_string = ''

    search.search_endpoint(SearchRequest())

    # add_items() must never be called, so that Kodi fails to open the directory
    assert not hasattr(kodi, 'screen_items')
