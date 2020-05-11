"""
Static variables to simplify for the IDE, and a proxy object for translation IDs
"""
from __future__ import absolute_import, division, unicode_literals


class AttributeProxy(object):
    """Run a function when getting attributes

    For example:
        p = AttributeProxy(function)
        p.x

    Will be the same as calling:
        function(AttributeProxy.x)
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
    """Setting IDs in Kodi"""
    RESOLUTION = 'video_res'
    HARD_SUBTITLES = 'subtitles'
    LANGUAGE = 'language'
    LANG_HIST = 'lang_history'
    LANG_NAME = 'lang_name'
    TOKEN = 'jwt_token'
    START_WARNING = 'startupmsg'
    SEARCH_TRANSL = 'search_tr'


class LocalizedStringID(AttributeProxy):
    """IDs for strings from PO file"""
    # Auto generated, by running this module directly
    RES = 30000
    P240 = 30001
    P360 = 30002
    P480 = 30003
    P720 = 30004
    P1080 = 30005
    LANG = 30010
    SET_LANG = 30011
    DISP_SUB = 30012
    HIDDEN = 30013
    CONV_QUESTION = 30014
    START_WARN = 30015
    THEO_WARN = 30016
    DISCLAIMER = 30020
    PLAY_LANG = 30021
    SHUFFLE_CAT = 30023
    AUDIO_ONLY = 30024
    CONN_ERR = 30025


def _generate_string_ids():
    # Py2: 'rb' gives us bytes in both Py2 and Py3 so we can decode it to unicode
    strings = open('../language/resource.language.en_gb/strings.po', 'rb').read().decode('utf-8')
    comment = None
    for line in strings.split('\n'):
        if line.startswith('# '):
            comment = line[2:].replace(' ', '_').upper()
        elif line.startswith('msgctxt') and comment:
            print('{} = {}'.format(comment, line[10:15]))
            comment = None


if __name__ == '__main__':
    _generate_string_ids()
