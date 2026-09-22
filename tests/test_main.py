import addon
from resources.lib.jwlib.media import NotFoundError
from resources.lib.kodi import LogLevel
from resources.lib.requests import (
    BrowseRequest, ConfigRequest, LanguageRequest, PlayRequest, SearchRequest, ShuffleRequest,
)


def _raise(exc):
    def raiser(*args, **kwargs):
        raise exc

    return raiser


def test_main_dispatches_to_browse(kodi, monkeypatch):
    calls = []
    monkeypatch.setattr(addon, 'browse_endpoint', lambda request: calls.append(request))
    request = BrowseRequest(category='CatKey', hidden=False, media=False)
    kodi.addon_query = '?' + request.query

    addon.main()

    assert calls == [request]


def test_main_dispatches_to_config(kodi, monkeypatch):
    calls = []
    monkeypatch.setattr(addon, 'config_endpoint', lambda request: calls.append(request))
    request = ConfigRequest(lang1='Z', label='Swedish')
    kodi.addon_query = '?' + request.query

    addon.main()

    assert calls == [request]


def test_main_dispatches_to_disclaimer(kodi, monkeypatch):
    calls = []
    monkeypatch.setattr(addon, 'show_disclaimer', lambda: calls.append(True))
    kodi.addon_query = '?mode=disclaimer'

    addon.main()

    assert calls == [True]


def test_main_dispatches_to_langlist(kodi, monkeypatch):
    calls = []
    monkeypatch.setattr(addon, 'langlist_endpoint', lambda request: calls.append(request))
    request = LanguageRequest(hidden=False, set_lang1=True)
    kodi.addon_query = '?' + request.query

    addon.main()

    assert calls == [request]


def test_main_dispatches_to_play(kodi, monkeypatch):
    calls = []
    monkeypatch.setattr(addon, 'play_endpoint', lambda request: calls.append(request))
    request = PlayRequest(media='MediaKey', hidden=False)
    kodi.addon_query = '?' + request.query

    addon.main()

    assert calls == [request]


def test_main_dispatches_to_search(kodi, monkeypatch):
    calls = []
    monkeypatch.setattr(addon, 'search_endpoint', lambda request: calls.append(request))
    request = SearchRequest(q='cats')
    kodi.addon_query = '?' + request.query

    addon.main()

    assert calls == [request]


def test_main_dispatches_to_shuffle(kodi, monkeypatch):
    calls = []
    monkeypatch.setattr(addon, 'shuffle_endpoint', lambda request: calls.append(request))
    request = ShuffleRequest(category='Cat', hidden=False)
    kodi.addon_query = '?' + request.query

    addon.main()

    assert calls == [request]


def test_main_defaults_to_home_when_mode_missing(kodi, monkeypatch):
    calls = []
    monkeypatch.setattr(addon, 'home_endpoint', lambda: calls.append(True))
    kodi.addon_query = ''

    addon.main()

    assert calls == [True]


def test_main_defaults_to_home_when_mode_unknown(kodi, monkeypatch):
    calls = []
    monkeypatch.setattr(addon, 'home_endpoint', lambda: calls.append(True))
    kodi.addon_query = '?mode=bogus'

    addon.main()

    assert calls == [True]


def test_main_handles_not_found_error(kodi, monkeypatch):
    logged = []
    monkeypatch.setattr(kodi, 'log', lambda message, level=LogLevel.INFO: logged.append(level))
    monkeypatch.setattr(addon, 'browse_endpoint', _raise(NotFoundError))
    kodi.addon_query = '?' + BrowseRequest(category='CatKey', hidden=False, media=False).query

    addon.main()

    assert kodi.notifications == ['STRING #30301']
    assert logged == [LogLevel.ERROR]


def test_main_handles_os_error(kodi, monkeypatch):
    logged = []
    monkeypatch.setattr(kodi, 'log', lambda message, level=LogLevel.INFO: logged.append(level))
    monkeypatch.setattr(addon, 'browse_endpoint', _raise(OSError))
    kodi.addon_query = '?' + BrowseRequest(category='CatKey', hidden=False, media=False).query

    addon.main()

    assert kodi.notifications == ['STRING #30300']
    assert logged == [LogLevel.ERROR]
