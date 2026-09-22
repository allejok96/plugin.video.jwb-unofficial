import pytest

from resources.lib.endpoints import langlist
from resources.lib.jwlib.media import Media, Language
from resources.lib.requests import ConfigRequest, LanguageRequest, PlayRequest, ShuffleRequest


@pytest.fixture
def swedish() -> Language:
    return Language(code='Z', iso='sv', name='Swedish', vernacular='Svenska')


def test_filter_languages(languages):
    filtered = list(langlist.filter_languages(languages, ['E', 'F']))
    assert [lang.code for lang in filtered] == ['E', 'F']


def test_sort_languages_recent_and_english_first(kodi, languages):
    kodi.settings['lang_history'] = 'F Z'

    sorted_langs = langlist.sort_languages(languages)

    assert [lang.code for lang in sorted_langs] == ['E', 'F', 'Z', 'D']


def test_format_language(swedish):
    assert langlist.format_language(swedish) == 'Swedish / Svenska'


def test_build_query_shuffle_category(kodi, swedish):
    request = LanguageRequest(hidden=True, shuffle_category='SomeCat')

    assert langlist.build_query(request, swedish) == ShuffleRequest(
        category='SomeCat', hidden=True, lang='Z'
    ).url


def test_build_query_play_media(kodi, swedish):
    request = LanguageRequest(hidden=False, play_media='SomeMedia')

    assert langlist.build_query(request, swedish) == PlayRequest(
        media='SomeMedia', hidden=False, lang='Z'
    ).url


def test_build_query_set_lang1(kodi, swedish):
    request = LanguageRequest(hidden=False, set_lang1=True)

    assert langlist.build_query(request, swedish) == ConfigRequest(
        lang1='Z', label='Swedish / Svenska'
    ).url


def test_build_query_set_lang2(kodi, swedish):
    request = LanguageRequest(hidden=False, set_lang2=True)

    assert langlist.build_query(request, swedish) == ConfigRequest(
        lang2='Z', label='Swedish / Svenska'
    ).url


def test_build_actions(kodi, languages):
    request = LanguageRequest(hidden=False, set_lang1=True)

    actions = langlist.build_actions(request, languages)

    assert 'Swedish / Svenska' in [a.label for a in actions]
    assert 'RunPlugin(' + ConfigRequest(lang1='Z', label='Swedish / Svenska').url + ')' in [a.command for a in actions]


def test_langlist_endpoint_selects_action(kodi, session):
    session.add_common_languages()

    request = LanguageRequest(hidden=False, set_lang1=True)
    kodi.user_choice = 1  # pick the second entry offered

    langlist.langlist_endpoint(request)

    assert kodi.executed_commands == ['RunPlugin(' + ConfigRequest(lang1='D', label='German / Deutsch').url + ')']


def test_langlist_endpoint_cancelled(kodi, session):
    session.add_common_languages()

    request = LanguageRequest(hidden=False, set_lang1=True)
    kodi.user_choice = -1  # user cancelled

    langlist.langlist_endpoint(request)

    assert kodi.executed_commands == []


def test_langlist_endpoint_filters_by_media_languages(kodi, session):
    session.add_common_languages()

    session.media['MediaKey'] = Media.create(title='Some video', key='MediaKey', languages=['Z'], session=session)

    request = LanguageRequest(hidden=False, play_media='MediaKey')
    kodi.user_choice  = 0  # only one option should be offered: Swedish

    langlist.langlist_endpoint(request)

    assert kodi.executed_commands == ['RunPlugin(' + PlayRequest(media='MediaKey', hidden=False, lang='Z').url + ')']
