"""
Static variables to simplify for the IDE, and a proxy object for translation IDs
"""
from __future__ import absolute_import, division, unicode_literals

API_BASE = 'https://data.jw-api.org/mediator/v1'
TRANSLATION_URL = API_BASE + '/translations/'
CATEGORY_URL = API_BASE + '/categories/'
MEDIA_URL = API_BASE + '/media-items/'
LANGUAGE_URL = API_BASE + '/languages/'

TOKEN_URL = 'https://b.jw-cdn.org/tokens/jworg.jwt'
SEARCH_URL = 'https://data.jw-api.org/search/query'


class AttributeProxy(object):
    """A class which runs a function when accessing its attributes

    For example:
        proxy = AttributeProxy(function)
        proxy.some_attribute

    Is the same as:
        function(AttributeProxy.some_attribute)
    """

    def __init__(self, function):
        self._func = function

    def __getattribute__(self, name):
        # Py2: getattribute is ok with unicode, as long as it's all ASCII characters
        custom_function = super(AttributeProxy, self).__getattribute__('_func')
        original_value = super(AttributeProxy, self).__getattribute__(name)
        return custom_function(original_value)


class Query(object):
    """Strings for URL queries to addon itself"""
    MODE = 'mode'
    CATKEY = 'category'
    LANGCODE = 'language'
    LANGNAME = 'lname'
    MEDIAKEY = 'media'
    STREAMKEY = 'category'


class Mode(object):
    """Modes for use with mode= query to addon itself"""
    LANGUAGES = 'languages'
    SET_LANG = 'set_language'
    SEARCH = 'search'
    HIDDEN = 'ask_hidden'
    PLAY = 'play'
    BROWSE = 'browse'
    STREAM = 'stream'


class SettingID(object):
    """IDs from settins.xml"""
    RESOLUTION = 'video_res'
    SUBTITLES = 'subtitles'
    LANGUAGE = 'language'
    LANG_HIST = 'lang_history'
    LANG_NAME = 'lang_name'
    LANG_NEXT = 'lang_next'
    TOKEN = 'jwt_token'
    START_WARNING = 'startupmsg'
    SEARCH_TRANSL = 'search_tr'
    REMEMBER_LANG = 'remember_lang'


class LocalizedStringID(AttributeProxy):
    """IDs from strings.po"""
    HIDDEN = 30013
    CONV_QUESTION = 30014
    START_WARN = 30015
    THEO_WARN = 30016
    DISCLAIMER = 30020
    PLAY_LANG = 30021
    SHUFFLE_CAT = 30023
    AUDIO_ONLY = 30024
    CONN_ERR = 30025
    NOT_AVAIL = 30027
