from typing import List

from resources.lib.jwlib.search import ResultPage, search
from resources.lib.jwlib.search.const import FILTER_AUDIO, FILTER_VIDEO


from resources.lib.requests import SearchRequest
from resources.lib.jwgui import create_search_result
from resources.lib.kodi import kodi, ListItem, ItemType
from resources.lib.settings import settings
from resources.lib.translations import *

__all__ = (
    'search_endpoint',
)


def show_search_box():
    query = kodi().input_dialog()
    if query:
        execute_search_request(query)


def execute_search_request(query: str) -> None:
    # When we want to open a folder we must use ActivateWindow, not RunPlugin
    # (RunAddon can do this too, but it's a poorly documented feature)
    kodi().execute('ActivateWindow(Videos, ' + SearchRequest(q=query).url + ')')


def create_audio_button(query: str) -> ListItem:
    return ListItem(
        title=tr(Audio_clips),
        url=SearchRequest(q=query, audio=True).url,
        type=ItemType.FOLDER,
    )


def create_next_button(next_page_url: str) -> ListItem:
    return ListItem(
        title=tr(Next_page),
        url=SearchRequest(page=next_page_url).url,
        type=ItemType.FOLDER
    )


def get_result_from_url(url: str):
    return ResultPage.from_url(url, token=settings.token)


def get_result_from_query(query: str, audio: bool):
    return search(
        query,
        filter_type=FILTER_AUDIO if audio else FILTER_VIDEO,
        language=settings.language,
        token=settings.token
    )


def is_first_page_of_videos(page: ResultPage) -> bool:
    return page.insight.filter != FILTER_AUDIO and page.insight.page == 1


def build_screen(page: ResultPage):
    settings.token = page.token

    items: List[ListItem] = []

    if is_first_page_of_videos(page):
        items.append(create_audio_button(page.insight.query))

    for r in page.results:
        items.append(create_search_result(r))

    if page.next is not None:
        items.append(create_next_button(page.next.url))

    kodi().add_items(items)


def search_endpoint(request: SearchRequest):
    """API endpoint that shows a search box or a list of search results"""

    if request.q:
        build_screen(
            get_result_from_query(request.q, request.audio)
        )
    elif request.page:
        build_screen(
            get_result_from_url(request.page)
        )
    else:
        show_search_box()
