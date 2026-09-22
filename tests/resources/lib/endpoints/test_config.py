import logging

import pytest

import resources.lib.settings
from resources.lib.endpoints import config_endpoint
from resources.lib.requests import ConfigRequest
from resources.lib.settings import settings


def test_config_endpoint_sets_lang1(kodi, sessions):
    sessions.add('Z').translations = {'hdgSearch': 'Sök'}

    config_endpoint(ConfigRequest(lang1='Z', label='TEST NAME 1'))

    assert settings.language == 'Z'
    assert kodi.get_setting('lang_name') == 'TEST NAME 1'
    assert settings.search_label == 'Sök'


def test_config_endpoint_sets_lang1_falls_back_when_translation_fetch_fails(kodi, sessions, caplog):
    sv = sessions.add('Z')

    with pytest.raises(NotImplementedError):
        sv.get_translations()

    with caplog.at_level(logging.DEBUG):
        config_endpoint(ConfigRequest(lang1='Z', label='TEST NAME 1'))

    assert settings.language == 'Z'
    assert settings.search_label == 'Search'
    assert ('resources.lib.settings', logging.DEBUG, 'Failed to find translation of search label') in caplog.record_tuples


def test_config_endpoint_sets_lang2(kodi):
    config_endpoint(ConfigRequest(lang2='D', label='TEST NAME 2'))

    assert settings.second_language == 'D'
    assert kodi.get_setting('second_language_name') == 'TEST NAME 2'



