import pytest

from resources.lib.endpoints import search
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
    item = search.create_audio_button('cats')

    assert item.type == ItemType.FOLDER
    assert item.url == SearchRequest(q='cats', audio=True).url


def test_create_next_button(kodi):
    item = search.create_next_button('https://example.org/next')

    assert item.type == ItemType.FOLDER
    assert item.url == SearchRequest(page='https://example.org/next').url


def test_show_search_box_with_query(kodi):
    kodi.user_string = 'cats'

    search.show_search_box()

    kodi.executed_commands = ['ActivateWindow(Videos, ' + SearchRequest(q='cats').url + ')']



def test_show_search_box_empty_query(kodi):
    kodi.user_string = ''

    search.show_search_box()

    assert kodi.executed_commands == []


def test_execute_search_request(kodi):
    search.execute_search_request('dogs')

    assert kodi.executed_commands == ['ActivateWindow(Videos, ' + SearchRequest(q='dogs').url + ')']


def test_get_result_from_query(kodi, monkeypatch):
    page = make_result_page()
    captured = {}

    def fake_search(query, *, filter_type, language, token):
        captured['args'] = (query, filter_type, language, token)
        return page

    monkeypatch.setattr(search, 'search', fake_search)
    settings.token = 'STORED_TOKEN'

    result = search.get_result_from_query('cats', audio=True)

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

    result = search.get_result_from_url('https://example.org/page2')

    assert result is page
    assert captured['args'] == ('https://example.org/page2', 'STORED_TOKEN')


def test_is_first_page_of_videos_true():
    page = make_result_page(filter_type=FILTER_VIDEO, page=1)
    assert search.is_first_page_of_videos(page) is True


def test_is_first_page_of_videos_false_when_audio():
    page = make_result_page(filter_type=FILTER_AUDIO, page=1)
    assert search.is_first_page_of_videos(page) is False


def test_is_first_page_of_videos_false_when_not_first_page():
    page = make_result_page(filter_type=FILTER_VIDEO, page=2)
    assert search.is_first_page_of_videos(page) is False


def test_build_screen_first_page_shows_audio_button(kodi):
    page = make_result_page(filter_type=FILTER_VIDEO, page=1)

    search.build_screen(page)

    assert settings.token == 'TOKEN'
    assert kodi.screen_items[0].url == SearchRequest(q='test', audio=True).url


def test_build_screen_second_page_hides_audio_button(kodi):
    page = make_result_page(filter_type=FILTER_VIDEO, page=2)

    search.build_screen(page)

    assert kodi.screen_items == []


def test_build_screen_includes_next_button(kodi):
    page = make_result_page(filter_type=FILTER_AUDIO, page=1, next_link='https://example.org/next')

    search.build_screen(page)

    assert kodi.screen_items[-1].url == SearchRequest(page='https://example.org/next').url


def test_search_endpoint_with_query(kodi, monkeypatch):
    page = make_result_page()
    monkeypatch.setattr(search, 'get_result_from_query', lambda q, audio: page)

    search.search_endpoint(SearchRequest(q='cats'))

    assert kodi.screen_items


def test_search_endpoint_with_page(kodi, monkeypatch):
    page = make_result_page()
    captured = {}

    def fake_get_result_from_url(url):
        captured['url'] = url
        return page

    monkeypatch.setattr(search, 'get_result_from_url', fake_get_result_from_url)

    request = SearchRequest(page='https://example.org/next')
    search.search_endpoint(request)

    assert kodi.screen_items
    assert captured['url'] == request.page


def test_search_endpoint_shows_search_box(kodi):

    with pytest.raises(AttributeError):
        search.search_endpoint(SearchRequest())

    kodi.user_string = ''
    search.search_endpoint(SearchRequest())
