# Licensed under the Apache License, Version 2.0
from __future__ import unicode_literals, division, print_function, absolute_import

import sys
import os.path
import json
import random

from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcplugin, py2_decode, py2_encode
from kodi_six.xbmc import LOGDEBUG, LOGINFO, LOGNOTICE, LOGWARNING, LOGERROR

try:
    from urllib.error import HTTPError, URLError
    from urllib.request import urlopen, Request
    from urllib.parse import parse_qs, urlencode
    from time import strftime

except ImportError:
    from urlparse import parse_qs as _parse_qs
    from urllib2 import urlopen, Request, HTTPError, URLError
    from urllib import urlencode as _urlencode
    from time import strftime as _strftime


    # Py2: urlencode only accepts byte strings
    def urlencode(query):
        # Dict[str, str] -> str
        return py2_decode(_urlencode({py2_encode(param): py2_encode(arg) for param, arg in query.items()}))


    # Py2: even if parse_qs accepts unicode, the return makes no sense
    def parse_qs(qs):
        # str -> Dict[str, List[str]]
        return {py2_decode(param): [py2_decode(a) for a in args]
                for param, args in _parse_qs(py2_encode(qs)).items()}


    # Py2: strftime returns byte string
    def strftime(format, t=None):
        return py2_decode(_strftime(py2_encode(format)))


    # Py2: When using str, we mean unicode string
    str = unicode

# Set to True for performance profiling
CPROFILE = False
CPROFILE_OUTPUT_DIR = '/tmp'

# Static names for valid URL queries and modes, to simplify for the IDE
Q_MODE = 'mode'
Q_CATKEY = 'category'
Q_LANGCODE = 'language'
Q_LANGFILTER = 'filter'
Q_MEDIAKEY = 'media'
Q_STREAMKEY = 'category'
M_LANGUAGES = 'languages'
M_SET_LANG = 'set_language'
M_SEARCH = 'search'
M_HIDDEN = 'ask_hidden'
M_PLAY = 'play'
M_BROWSE = 'browse'
M_STREAM = 'stream'
M_PLAY_NODUB = 'nondubbed'

# To send stuff to the screen
addon_handle = int(sys.argv[1])
# To get settings and info
addon = xbmcaddon.Addon()
# For logging purpose
addon_id = addon.getAddonInfo('id')
# To to get translated strings
getstr = addon.getLocalizedString

vres = addon.getSetting('video_res')
video_res = [1080, 720, 480, 360, 240][int(vres)]
hard_subtitles_setting = addon.getSetting('subtitles') == 'true'
language = addon.getSetting('language')
if not language:
    language = 'E'


def log(msg, level=LOGDEBUG):
    xbmc.log(addon_id + ': ' + msg, level)


class Directory(object):
    def __init__(self, key=None, url=None, title=None, icon=None, fanart=None, hidden=False, description=None,
                 is_folder=True, streamable=False):
        """An object containing metadata for a folder"""

        self.key = key
        self.url = url
        self.title = title
        self.icon = icon
        self.fanart = fanart
        self.hidden = hidden
        self.description = description
        self.is_folder = is_folder
        self.streamable = streamable

    def __bool__(self):
        """Is everything ok?"""

        # Never show hidden directories
        if self.hidden:
            return False
        elif not self.key:
            log('category has no "key" metadata, skipping', LOGWARNING)
            return False
        else:
            return True

    __nonzero__ = __bool__

    def parse_common(self, data):
        """Constructor from common metadata"""
        self.description = data.get('description')

        # Note about tags
        # RokuExclude, FireTVExclude, AppleTVExclude are set-top boxes like Kodi, we should use one of these
        # WebExclude = deprecated? may be tv.jw.org
        # RWSLExclude = Sign Language?
        # JWORGExclude vs WWWExclude, what's the difference?
        # Library[Tag] has something to do with the new changes to jw.org
        self.hidden = 'AppleTVExclude' in data.get('tags', [])

        # Note about image abbreviations
        # Last letter: s is smaller, r/h is bigger
        # pss/psr 3:4
        # sqs/sqr 1:1
        # cvr     1:1
        # rps/rph 5:4
        # wss/wsr 16:9
        # lsr/lss 2:1
        # pns/pnr 3:1
        self.icon = getitem(data, 'images', ('sqr', 'cvr'), ('lg', 'md'))
        # Note: don't overwrite fanart choice (in main menu)
        if not self.fanart:
            self.fanart = getitem(data, 'images', ('wsr', 'lsr', 'pnr'), ('md', 'lg'))

    def parse_category(self, data):
        """Constructor taking jw category metadata

        :param data: deserialized JSON data from jw.org
        """
        self.parse_common(data)
        self.key = data.get('key')
        self.title = data.get('name')

        tags = data.get('tags', [])
        if 'StreamThisChannelEnabled' in tags or 'AllowShuffleInCategoryHeader' in tags:
            self.streamable = True

        self.url = request_to_self({Q_MODE: M_BROWSE, Q_STREAMKEY: self.key})

    def listitem(self):
        """Create a Kodi listitem from the metadata"""

        try:
            # offscreen is a Kodi v18 feature
            # We wont't be able to change the listitem after running .addDirectoryItem()
            # But load time for this function is cut down by 93% (!)
            li = xbmcgui.ListItem(self.title, offscreen=True)
        except TypeError:
            li = xbmcgui.ListItem(self.title)
        art_dict = {'icon': self.icon, 'poster': self.icon, 'fanart': self.fanart}
        # Check if there's any art, setArt can be kinda slow
        if max(v for v in art_dict.values()):
            li.setArt(art_dict)
        li.setInfo('video', {'plot': self.description})

        if self.streamable:
            query = {Q_MODE: M_STREAM, Q_STREAMKEY: self.key}
            action = 'RunPlugin(' + request_to_self(query) + ')'
            li.addContextMenuItems([(getstr(30007), action)])

        return li

    def listitem_with_path(self):
        """Return ListItem with path set, because apparently setPath() is slow"""

        li = self.listitem()
        li.setPath(self.url)
        return li

    def add_item_in_kodi(self):
        """Adds this as a directory item in Kodi"""

        xbmcplugin.addDirectoryItem(handle=addon_handle, url=self.url, listitem=self.listitem(),
                                    isFolder=self.is_folder)


class Media(Directory):
    def __init__(self, duration=None, media_type='video', languages=None, publish_date=None,
                 size=None, is_folder=False, subtitles=None, **kwargs):
        """An object containing metadata for a video or audio recording"""

        super(Media, self).__init__(**kwargs)
        self.media_type = media_type
        self.size = size
        self.languages = languages
        if self.languages is None:
            self.languages = []
        self.__publish_date = publish_date
        self.__duration = duration
        self.is_folder = is_folder
        self.subtitles = subtitles

    def __bool__(self):
        """Is everything ok?"""

        if self.hidden and not self.key:
            log('hidden media has no "key" metadata, skipping', LOGWARNING)
        elif not self.hidden and not self.url:
            log('media has no playable files, skipping', LOGWARNING)
        else:
            return True

    __nonzero__ = __bool__

    def parse_media(self, data, censor_hidden=True):
        """Constructor taking jw media metadata

        :param data: deserialized JSON data from jw.org
        :param censor_hidden: if True, media marked as hidden will ask for permission before being displayed
        """
        self.parse_common(data)
        self.key = data.get('languageAgnosticNaturalKey')

        if self.hidden and censor_hidden:
            # Reset to these values
            self.__init__(title=getstr(30013),
                          url=request_to_self({Q_MODE: M_HIDDEN, Q_MEDIAKEY: self.key}),
                          is_folder=True)
        else:
            self.url, self.size, self.subtitles = self.get_preferred_media_file(data.get('files', []))
            self.title = data.get('title')
            if data.get('type') == 'audio':
                self.media_type = 'music'
            self.duration = data.get('duration')
            self.publish_date = data.get('firstPublished')
            self.languages = data.get('availableLanguages', [])

    def parse_hits(self, data):
        """Create an instance of Media out of search results

        :param data: deserialized search result JSON data from jw.org
        """
        self.title = data.get('displayTitle')
        if 'type:audio' in data.get('tags', []):
            self.media_type = 'music'
            self.title += ' ' + getstr(30008)
        self.key = data.get('languageAgnosticNaturalKey')
        self.publish_date = data.get('firstPublishedDate')
        if self.key:
            self.url = request_to_self({Q_MODE: M_PLAY, Q_MEDIAKEY: self.key})

        for m in data.get('metadata', []):
            if m.get('key') == 'duration':
                self.duration = m.get('value')

        # TODO? We could try for pnr and cvr images too, but I'm too lazy, and no one cares about search anyway
        for i in data.get('images', []):
            if i.get('size') == 'md' and i.get('type') == 'sqr':
                self.icon = i.get('url')
            if i.get('size') == 'md' and i.get('type') == 'lsr':
                self.fanart = i.get('url')

    @property
    def publish_date(self):
        return self.__publish_date

    @publish_date.setter
    def publish_date(self, value):
        """Value is a string like 2017-05-18T15:41:52.197Z"""

        # Dates are not visible in default skin, all this does is slow down processing
        # try: self.__publish_date = time.strptime(value[0:19], '%Y-%m-%dT%H:%M:%S')
        # except (ValueError, TypeError): pass

        pass

    @property
    def duration(self):
        return self.__duration

    @duration.setter
    def duration(self, value):
        try:
            self.__duration = int(value)
            return
        except (TypeError, ValueError):
            pass
        try:
            t = value.split(':')
            if len(value) == 3:
                self.__duration = int(t[0]) * 60 * 60 + int(t[1]) * 60 + int(t[2])
            elif len(t) == 2:
                self.__duration = int(t[0]) * 60 + int(t[1])
            elif len(t) == 1:
                self.__duration = int(t[0])
        except (ValueError, TypeError):
            pass

    @staticmethod
    def get_preferred_media_file(data):
        """Take an jw JSON array of files and metadata and return the most suitable like (url, size, subtitles)"""

        # Rank media files depending on how they match certain criteria
        # Video resolution will be converted to a rank between 2 and 10
        resolution_not_too_big = 200
        subtitles_matches_pref = 100

        files = []
        for f in data:
            rank = 0
            try:
                # Grab resolution from label, eg. 360p, and remove the p
                res = int(f.get('label')[:-1])
            except (TypeError, ValueError):
                try:
                    res = int(f.get('frameHeight', 0))
                except (TypeError, ValueError):
                    res = 0
            rank += res // 10
            if 0 < res <= video_res:
                rank += resolution_not_too_big
            # 'subtitled' only applies to hardcoded video subtitles
            if f.get('subtitled') == hard_subtitles_setting:
                rank += subtitles_matches_pref
            files.append((rank, f))
        files.sort()

        if len(files) > 0:
            # [-1] The file with the highest rank, [1] the filename, not the rank
            f = files[-1][1]
            return f['progressiveDownloadURL'], f['filesize'], getitem(f, 'subtitles', 'url', default=None)
        else:
            return None, None, None

    def listitem(self):
        """Create a Kodi listitem from the metadata"""

        art_dict = {
            'icon': self.icon,
            'poster': self.icon,
            'fanart': self.fanart
        }
        info_dict = {
            'duration': self.duration,
            'title': self.title,
            'size': self.size
        }

        if self.media_type == 'music':
            info_dict['comment'] = self.description
        else:
            info_dict['plot'] = self.description

        if self.publish_date:
            info_dict['date'] = strftime('%d.%m.%Y', self.publish_date)
            info_dict['year'] = strftime('%Y', self.publish_date)

        try:
            # Kodi v18
            li = xbmcgui.ListItem(self.title, offscreen=True)
        except TypeError:
            li = xbmcgui.ListItem(self.title)

        li.setArt(art_dict)
        li.setInfo(self.media_type, info_dict)

        if self.url:
            # For some reason needed by xbmcplugin.setResolvedUrl
            li.setProperty("isPlayable", "true")
        if self.subtitles:
            li.setSubtitles([self.subtitles])

        context_menu = []

        # Play in other language context menu
        if self.key:
            query = {Q_MODE: M_LANGUAGES, Q_MEDIAKEY: self.key}
            if self.languages:
                query[Q_LANGFILTER] = ' '.join(self.languages)
            # Note: Use RunPlugin instead of RunAddon, because an add-on assumes a folder view
            action = 'RunPlugin(' + request_to_self(query) + ')'
            context_menu.append((getstr(30006), action))

        # Play in English with subtitles
        if self.key and self.subtitles and language != 'E':
            query = {Q_MODE: M_PLAY_NODUB, Q_MEDIAKEY: self.key}
            if self.languages:
                query[Q_LANGFILTER] = ' '.join(self.languages)
            action = 'PlayMedia(' + request_to_self(query) + ')'
            context_menu.append((getstr(30022), action))

        if context_menu:
            li.addContextMenuItems(context_menu)

        return li


def getitem(obj, *keys, **kwargs):
    """Recursive get function

    Keys are checked in order, and the first found value is returned

    :param obj: list, dictionary or tuple
    :param keys: a index or a key name or a tuple with indexes and key names
    :keyword default: value to return if it fails
    :keyword fail: used internally

    Example: getitem(colorlist, ('red', 'green'), 2)

    Would match: colorlist['red'][2] or colorlist['green'][2]
    """
    assert keys
    sublevels = list(keys)
    toplevels = sublevels.pop(0)

    if type(toplevels) != tuple:
        toplevels = (toplevels,)

    for toplevel in toplevels:
        try:
            if len(sublevels) > 0:
                # More levels, go deeper
                return getitem(obj[toplevel], *sublevels, fail=True)
            else:
                # Last level, return value
                return obj[toplevel]
        except (TypeError, KeyError, IndexError):
            # Could not get value, try next
            continue

    # Py2: get() unicode is ok
    if kwargs.get('fail', False):
        # No keys existed for this level, return to parent
        raise KeyError
    else:
        # Everything failed, we return nicely
        return kwargs.get('default')


def get_json(url, on_fail='exit'):
    """Fetch JSON data from an URL and return it as a Python object

    :param url: URL to open or a Request object
    :param on_fail: string, what to do on a URLError: exit, log, error

    exit - issue a notification to Kodi and exit the plugin instance (default)
    log - print to the log and return None
    error - raise an error
    """
    try:
        if type(url) == str:
            log('opening ' + url, LOGINFO)
        elif isinstance(url, Request):
            log('opening ' + url.get_full_url(), LOGINFO)
        data = urlopen(url).read().decode('utf-8')
    except URLError as e:
        if on_fail == 'log':
            log('{}: {}'.format(url, e.reason), LOGWARNING)
            return None
        elif on_fail == 'exit':
            log('{}: {}'.format(url, e.reason), LOGERROR)
            xbmcgui.Dialog().notification(
                addon.getAddonInfo('name'),
                getstr(30009),
                icon=xbmcgui.NOTIFICATION_ERROR)
            # Don't raise an error, it will just generate another cryptic notification in Kodi
            exit()
        else:
            raise e
    else:
        return json.loads(data)


def get_jwt_token(update=False):
    """Get temporary authentication token from memory, or jw.org"""

    token = addon.getSetting('jwt_token')
    if not token or update is True:
        log('requesting new authentication token from tv.jw.org', LOGINFO)
        url = 'https://tv.jw.org/tokens/web.jwt'
        token = urlopen(url).read().decode('utf-8')
        if token != '':
            addon.setSetting('jwt_token', token)
    return token


def top_level_page():
    """The main menu, media categories from tv.jw.org plus extra stuff"""

    default_fanart = os.path.join(addon.getAddonInfo('path'), addon.getAddonInfo('fanart'))

    if addon.getSetting('startupmsg') == 'true':
        dialog = xbmcgui.Dialog()
        if dialog.yesno(getstr(30016), getstr(30017),
                        nolabel=getstr(30018), yeslabel=getstr(30019)):
            dialog.textviewer(getstr(30016), getstr(30020))

    data = get_json('https://data.jw-api.org/mediator/v1/categories/' + language + '?detailed=True')

    for c in data['categories']:
        d = Directory(fanart=default_fanart)
        d.parse_category(c)
        if d:
            d.add_item_in_kodi()

    # Get "search" translation from internet - overkill but so cool
    # Try cache first, to speed up loading
    search_label = addon.getSetting('search_tr')
    if not search_label:
        data = get_json('https://data.jw-api.org/mediator/v1/translations/' + language, on_fail='log')
        search_label = getitem(data, 'translations', language, 'hdgSearch', default='Search')
        addon.setSetting('search_tr', search_label)
    d = Directory(url=request_to_self({Q_MODE: M_SEARCH}), title=search_label, fanart=default_fanart,
                  icon='DefaultMusicSearch.png')
    d.add_item_in_kodi()

    xbmcplugin.endOfDirectory(addon_handle)


def sub_level_page(sub_level):
    """A sub-level page with either folders or playable media"""

    # TODO: less detailed request?
    #  For categories like VODStudio that contains subcategories with media,
    #  all media is included in the response, which slows down the parsing a lot.
    #  All this extra data has no function in this script. If there only was a way
    #  to request the subcategories, but without their media...
    data = get_json('https://data.jw-api.org/mediator/v1/categories/' + language + '/' + sub_level + '?&detailed=1')
    data = data['category']

    # Enable more viewtypes
    if data.get('type') == 'ondemand':
        xbmcplugin.setContent(addon_handle, 'videos')

    if 'subcategories' in data:
        for sc in data['subcategories']:
            d = Directory()
            d.parse_category(sc)
            if d:
                d.add_item_in_kodi()
    if 'media' in data:
        for md in data['media']:
            m = Media()
            m.parse_media(md)
            if m:
                m.add_item_in_kodi()

    xbmcplugin.endOfDirectory(addon_handle)


def shuffle_category(key):
    """Generate a shuffled playlist and start playing"""

    data = get_json('https://data.jw-api.org/mediator/v1/categories/' + language + '/' + key + '?&detailed=1')
    data = data['category']
    all_media = data.get('media', [])
    for sc in data.get('subcategories', []):  # type: dict
        # Don't include things like Featured, because that would become duplicate
        if 'AllowShuffleInCategoryHeader' in sc.get('tags', []):
            all_media += sc.get('media', [])

    # Shuffle in place, we don't want to mess with Kodi's settings
    random.shuffle(all_media)

    pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    pl.clear()

    for md in all_media:
        media = Media()
        media.parse_media(md, censor_hidden=False)
        if media and not media.hidden:
            pl.add(media.url, media.listitem_with_path())

    xbmc.Player().play(pl)


def language_dialog(media_key=None, valid_langs=None):
    """Display a list of languages and set the global language setting

    :param media_key: play this media file instead of changing global setting
    :param valid_langs: space separated list of language codes, for filtering
    """
    # Note: the list from jw.org is already sorted by ['name']
    data = get_json('http://data.jw-api.org/mediator/v1/languages/' + language + '/web')
    # Convert language data to a list of tuples with (code, name)
    languages = [(l.get('code'), l.get('name', '') + ' / ' + l.get('vernacular', ''))
                 for l in data['languages']]
    # Get the languages matching the ones from history and put them first
    history = addon.getSetting('lang_history').split()
    languages = [l for h in history for l in languages if l[0] == h] + languages

    if valid_langs:
        languages = [l for l in languages if l[0] in valid_langs.split()]

    dialog_strings = []
    dialog_actions = []
    for code, name in languages:
        dialog_strings.append(name)
        if media_key:
            request = request_to_self({
                Q_MODE: M_PLAY,
                Q_MEDIAKEY: media_key,
                Q_LANGCODE: code})
            dialog_actions.append('PlayMedia(' + request + ')')
        else:
            request = request_to_self({Q_MODE: M_SET_LANG, Q_LANGCODE: code})
            dialog_actions.append('RunPlugin(' + request + ')')

    selection = xbmcgui.Dialog().select('', dialog_strings)
    if selection >= 0:
        xbmc.executebuiltin(dialog_actions[selection])


def set_language(lang):
    """Save a language to setting and history"""

    addon.setSetting('language', lang)
    save_language_history(lang)
    # Forget about the translation of "Search"
    addon.setSetting('search_tr', '')


def save_language_history(lang):
    """Save a language code first in history"""

    history = addon.getSetting('lang_history').split()
    history = [lang] + [h for h in history if h != lang]
    history = history[0:5]
    addon.setSetting('lang_history', ' '.join(history))


def search_page():
    """Display a search dialog, then the results"""

    kb = xbmc.Keyboard()
    kb.doModal()
    if kb.isConfirmed():
        # Enable more viewtypes
        xbmcplugin.setContent(addon_handle, 'videos')

        search_string = kb.getText()
        url = 'https://data.jw-api.org/search/query?'
        query = urlencode({'q': search_string, 'lang': language, 'limit': 24})
        headers = {'Authorization': 'Bearer ' + get_jwt_token()}
        try:
            data = get_json(Request(url + query, headers=headers), on_fail='error')
        except HTTPError as e:
            if e.code == 401:
                headers = {'Authorization': 'Bearer ' + get_jwt_token(True)}
                data = get_json(Request(url + query, headers=headers))
            else:
                raise e

        for hd in data['hits']:
            media = Media()
            media.parse_hits(hd)
            if media:
                media.add_item_in_kodi()

        xbmcplugin.endOfDirectory(addon_handle)


def hidden_media_dialog(media_key):
    """Ask the user for permission, then create a folder with a single media entry"""

    dialog = xbmcgui.Dialog()
    if dialog.yesno(getstr(30013), getstr(30014)):
        url = 'https://data.jw-api.org/mediator/v1/media-items/' + language + '/' + media_key
        data = get_json(url)
        media = Media()
        media.parse_media(data['media'][0], censor_hidden=False)
        if media:
            media.add_item_in_kodi()
        else:
            raise RuntimeError
        xbmcplugin.endOfDirectory(addon_handle)


def resolve_media(media_key, lang=None, nondubbed=False):
    """Resolve to a playable URL for a media key name, as found in tv.jw.org URLs

    :param media_key: string, media to play
    :param lang: string, language code
    :param nondubbed: Play in English, with localized subtitles

    When language is specified, play video in that language, and save language in history
    """
    if nondubbed:
        lang = 'E'
    elif lang:
        save_language_history(lang)

    url = 'https://data.jw-api.org/mediator/v1/media-items/' + (lang or language) + '/' + media_key
    data = get_json(url)
    media = Media()
    media.parse_media(data['media'][0], censor_hidden=False)

    if nondubbed:
        l_url = 'https://data.jw-api.org/mediator/v1/media-items/' + language + '/' + media_key
        l_data = get_json(l_url)
        l_media = Media()
        l_media.parse_media(l_data['media'][0], censor_hidden=False)
        if l_media:
            media.subtitles = l_media.subtitles

    if media:
        xbmcplugin.setResolvedUrl(addon_handle, succeeded=True, listitem=media.listitem_with_path())
    else:
        raise RuntimeError


def request_to_self(query):
    """Return a string with an URL request to the add-on itself"""

    # argv[0] is path to the plugin
    return sys.argv[0] + '?' + urlencode(query)


def main():
    # Tested in Kodi 18: This will disable all viewtypes but list and icons won't be displayed within the list
    xbmcplugin.setContent(addon_handle, 'files')

    mode = args.get(Q_MODE)

    if mode is None:
        top_level_page()
    elif mode == M_LANGUAGES:
        language_dialog(args.get(Q_MEDIAKEY), args.get(Q_LANGFILTER))
    elif mode == M_SET_LANG:
        set_language(args[Q_LANGCODE])
    elif mode == M_HIDDEN:
        hidden_media_dialog(args[Q_MEDIAKEY])
    elif mode == M_SEARCH:
        search_page()
    elif mode == M_PLAY:
        resolve_media(args[Q_MEDIAKEY], args.get(Q_LANGCODE))
    elif mode == M_PLAY_NODUB:
        resolve_media(args[Q_MEDIAKEY], args.get(Q_LANGCODE), nondubbed=True)
    elif mode == M_BROWSE:
        sub_level_page(args[Q_CATKEY])
    elif mode == M_STREAM:
        shuffle_category(args[Q_STREAMKEY])
    # Backwards compatibility
    elif mode.startswith('Streaming') and mode != 'Streaming':
        shuffle_category(mode)
    else:
        sub_level_page(mode)


if __name__ == '__main__':
    # The awkward way Kodi passes arguments to the add-on...
    # argv[2] is a URL query string, probably passed by request_to_self()
    # example: ?mode=play&media=ThisVideo
    args = parse_qs(sys.argv[2][1:])
    # parse_qs puts the values in a list, so we grab the first value for each key
    args = {k: v[0] for k, v in args.items()}

    if CPROFILE:
        import cProfile

        output = '{}/{}-{}-{}.cprof'.format(CPROFILE_OUTPUT_DIR,
                                            strftime('%y%m%d%H%M%S'),
                                            args.get(Q_MODE),
                                            args.get(Q_CATKEY) or args.get(Q_MEDIAKEY))
        log('saving cProfile output to ' + output)
        cProfile.run('main()', output)
    else:
        main()
