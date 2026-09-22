from dataclasses import dataclass

import pytest

from resources.lib.requests import (
    BrowseRequest, ConfigRequest, LanguageRequest, PlayRequest, _Request, ShuffleRequest,
)


@dataclass
class DummyRequest(_Request):
    """Stand-in Request subclass used to test the from_dict()/default_values mechanism
    in isolation, without depending on the invariants of any real endpoint's Request.
    """
    mode = 'dummy'
    default_values = {'count': 0, 'flag': False}

    name: str
    count: int
    flag: bool
    label: str = ''


def test_empty_and_false_are_excluded():
    assert PlayRequest(media='', hidden=False).query == 'mode=play'


def test_true_becomes_1():
    assert PlayRequest(media='M', hidden=True).query == 'mode=play&media=M&hidden=1'
    assert PlayRequest.from_dict({'media': 'M', 'hidden': '1'}) == PlayRequest(media='M', hidden=True)


def test_query_excludes_empty_values():
    assert ConfigRequest(lang1='Z').query == 'mode=config&lang1=Z'


def test_query_includes_only_non_default_fields():
    assert ConfigRequest(lang1='Z').query == 'mode=config&lang1=Z'


def test_query_urlencodes_special_characters():
    query = ConfigRequest(lang1='Z', label='A & B / C').query
    assert query == 'mode=config&lang1=Z&label=A+%26+B+%2F+C'


def test_url_combines_addon_id_and_query(kodi):
    request = ConfigRequest(lang1='Z', label='Swedish')
    assert request.url == f'plugin://{kodi.get_addon_id()}/?{request.query}'


def test_url_format():
    assert ConfigRequest(lang1='Z').url == 'plugin://plugin.video.jwb-unofficial/?mode=config&lang1=Z'


def test_play_request_compatibility():
    assert PlayRequest(media='MediaKey',
                       hidden=False).url == 'plugin://plugin.video.jwb-unofficial/?mode=play&media=MediaKey'


#
# default_values / from_dict()
#
# `default_values` makes an attribute mandatory when a Request is constructed directly
# (e.g. by internal code), but optional (falling back to the given default) when built via
# from_dict() (e.g. from a Kodi bookmark URL, which may be old or malformed).
#

def test_field_without_dataclass_default_is_required_by_constructor():
    with pytest.raises(TypeError):
        DummyRequest(name='x')  # 'count' and 'flag' are missing


def test_from_dict_fills_in_missing_fields_from_default_values():
    assert DummyRequest.from_dict({'name': 'x'}) == DummyRequest(name='x', count=0, flag=False)


def test_from_dict_prefers_user_args_over_default_values():
    request = DummyRequest.from_dict({'name': 'x', 'count': '5', 'flag': '1'})
    assert request == DummyRequest(name='x', count=5, flag=True)


def test_from_dict_converts_types():
    request = DummyRequest.from_dict({'name': 'x', 'count': '5', 'flag': '0'})
    assert request.count == 5
    assert request.flag is False


def test_from_dict_ignores_unknown_keys():
    request = DummyRequest.from_dict({'name': 'x', 'count': '1', 'flag': '1', 'bogus': 'y'})
    assert request == DummyRequest(name='x', count=1, flag=True)


def test_from_dict_still_requires_fields_without_a_default_values_entry():
    with pytest.raises(TypeError):
        DummyRequest.from_dict({'count': '1', 'flag': '1'})  # 'name' has no default_values entry


def test_from_dict_rejects_mismatched_default_value_type():
    @dataclass
    class BadDefaultRequest(_Request):
        mode = 'bad'
        default_values = {'count': 'not-an-int'}

        count: int

    with pytest.raises(AssertionError):
        BadDefaultRequest.from_dict({})


def test_from_dict_rejects_unsupported_field_type():
    @dataclass
    class UnsupportedTypeRequest(_Request):
        mode = 'unsupported'

        value: float

    with pytest.raises(RuntimeError):
        UnsupportedTypeRequest.from_dict({'value': '1.5'})


def test_browse_request_hidden_and_media_are_soft_defaults():
    with pytest.raises(TypeError):
        BrowseRequest(category='CatKey')  # 'hidden' and 'media' are required

    assert BrowseRequest.from_dict({'category': 'CatKey'}) == BrowseRequest(
        category='CatKey', hidden=False, media=False)
    assert BrowseRequest.from_dict({'category': 'CatKey', 'hidden': '1', 'media': '1'}) == BrowseRequest(
        category='CatKey', hidden=True, media=True)


def test_play_request_hidden_is_a_soft_default():
    with pytest.raises(TypeError):
        PlayRequest(media='M')  # 'hidden' is required

    assert PlayRequest.from_dict({'media': 'M'}) == PlayRequest(media='M', hidden=False)


def test_shuffle_request_hidden_is_a_soft_default():
    with pytest.raises(TypeError):
        ShuffleRequest(category='Cat')  # 'hidden' is required

    assert ShuffleRequest.from_dict({'category': 'Cat'}) == ShuffleRequest(category='Cat', hidden=False)


def test_language_request_hidden_is_a_soft_default():
    with pytest.raises(TypeError):
        LanguageRequest(play_media='M')  # 'hidden' is required

    assert LanguageRequest.from_dict({'play_media': 'M'}) == LanguageRequest(hidden=False, play_media='M')


#
# __post_init__ "never empty" assertions
#

def test_config_request_cannot_be_created_empty():
    with pytest.raises(AssertionError):
        ConfigRequest()


def test_config_request_allows_lang1_only():
    ConfigRequest(lang1='Z')


def test_config_request_allows_lang2_only():
    ConfigRequest(lang2='Z')


def test_language_request_cannot_be_created_empty():
    with pytest.raises(AssertionError):
        LanguageRequest(hidden=False)

    with pytest.raises(AssertionError):
        LanguageRequest.from_dict({})  # 'hidden' defaults to False, but nothing else is set


@pytest.mark.parametrize('kwargs', [
    {'play_media': 'M'},
    {'set_lang1': True},
    {'set_lang2': True},
    {'shuffle_category': 'Cat'},
])
def test_language_request_allows_any_single_action(kwargs):
    LanguageRequest(hidden=False, **kwargs)
