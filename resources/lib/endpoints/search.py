from typing import List

from resources.lib.jwlib.search import ResultPage, search
from resources.lib.jwlib.search.const import FILTER_AUDIO, FILTER_VIDEO

from resources.lib.jwgui import create_search_result
from resources.lib.kodi import kodi, ListItem, ItemType
from resources.lib.requests import SearchRequest
from resources.lib.settings import settings
from resources.lib.translations import *


def _create_audio_button(query: str) -> ListItem:
    return ListItem(
        title=tr(Audio_clips),
        url=SearchRequest(q=query, audio=True).url,
        type=ItemType.FOLDER,
    )


def _create_next_button(next_page_url: str) -> ListItem:
    return ListItem(
        title=tr(Next_page),
        url=SearchRequest(page=next_page_url).url,
        type=ItemType.FOLDER
    )


def _get_result_from_url(url: str):
    return ResultPage.from_url(url, token=settings.token)


def _get_result_from_query(query: str, audio: bool):
    return search(
        query,
        filter_type=FILTER_AUDIO if audio else FILTER_VIDEO,
        language=settings.language,
        token=settings.token
    )


def _is_first_page_of_videos(page: ResultPage) -> bool:
    return page.insight.filter != FILTER_AUDIO and page.insight.page == 1


def _build_screen(page: ResultPage):
    settings.token = page.token

    items: List[ListItem] = []

    if _is_first_page_of_videos(page):
        items.append(_create_audio_button(page.insight.query))

    for r in page.results:
        items.append(create_search_result(r))

    if page.next is not None:
        items.append(_create_next_button(page.next.url))

    kodi().add_items(items)


def search_endpoint(request: SearchRequest):
    """API endpoint that shows a search box or a list of search results"""

    if request.page:
        _build_screen(
            _get_result_from_url(request.page)
        )

    else:

        # TODO pressing OK should open a new page
        # The easy design is to open the search page like a directory and let it block until
        # the user has typed a query. This has a drawback: when the user navigates back from the second page,
        # Kodi may reload page 1 and open the keyboard again... I don't know how to fix that.
        # I tried experimenting with having the dialog box call either of these things when OK is pressed:
        # - ActivateWindow(Videos, plugin://plugin.video.jwb-unofficial?mode=search&q=query)
        # - RunAddon(plugin.video.jwb-unofficial, mode=search&q=query)
        #   (RunAddon opens a folder view, RunPlugin just executes in the background... I think)
        # But neither seems to work because it can't switch window when there's a modal dialog on top.
        search_term = request.q or kodi().input_dialog()

        if search_term:
            _build_screen(
                _get_result_from_query(search_term, request.audio)
            )
        else:
            # If kodi().add_items() is never called, it will fail to open the directory with
            # GetDirectory(plugin://plugin.video.jwb-unofficial/?mode=search) failed
            # and this is exactly what we want if the user presses Cancel.
            pass
