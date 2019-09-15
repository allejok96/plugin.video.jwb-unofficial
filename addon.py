# Licensed under the Apache License, Version 2.0
import sys
import os.path
import time
import urllib
import urllib2
import urlparse

import xbmcplugin
import xbmcaddon
import xbmcgui
import xbmc

try:
    import json
except ImportError:
    import simplejson as json

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

# The awkward way Kodi passes arguments to the add-on...
# argv[0] is the plugin path
# argv[1] is the add-on handle, whatever that means, unique to this instance
addon_handle = int(sys.argv[1])
# argv[2] is the URL query string, probably passed by request_to_self()
# example: ?mode=play&media=ThisVideo
args = urlparse.parse_qs(sys.argv[2][1:])
# parse_qs puts the values in a list, so we grab the first value for each key
args = {k: v[0] for k, v in args.items()}

addon = xbmcaddon.Addon()
getstr = addon.getLocalizedString

# Tested in Kodi 18: This will disable all viewtypes but list and icons won't be displayed within the list
xbmcplugin.setContent(addon_handle, 'files')

vres = addon.getSetting('video_res')
video_res = [1080, 720, 480, 360, 240][int(vres)]
subtitles = addon.getSetting('subtitles') == 'true'
language = addon.getSetting('language')
if not language:
    language = 'E'


class Directory(object):
    def __init__(self, key=None, url=None, title=None, icon=None, fanart=None, hidden=False, description=None,
                 is_folder=True):
        """An object containing metadata for a folder"""

        self.key = key
        self.url = url
        self.title = title
        self.icon = icon
        self.fanart = fanart
        self.hidden = hidden
        self.description = description
        self.is_folder = is_folder

    @classmethod
    def parse_common(cls, data):
        """Constructor from common metadata"""

        c = cls()
        c.description = data.get('description')
        c.hidden = 'WebExclude' in data.get('tags', [])

        # A note on image abbreviations
        # Last letter: s is smaller, r/h is bigger
        # pss/psr 3:4
        # sqs/sqr 1:1
        # cvr     1:1
        # rps/rph 5:4
        # wss/wsr 16:9
        # lsr/lss 2:1
        # pns/pnr 3:1
        c.icon = getr(data, ['images', ('sqr', 'cvr'), ('lg', 'md')])
        c.fanart = getr(data, ['images', ('wsr', 'lsr', 'pnr'), ('md', 'lg')])

        return c

    @classmethod
    def parse_category(cls, data):
        """Constructor taking jw category metadata

        :param data: deserialized JSON data from jw.org
        """
        c = cls.parse_common(data)
        if c.hidden:
            # Never any hidden directories
            return None

        c.key = data.get('key')
        if not c.key:
            xbmc.log('category has no "key" metadata, skipping', xbmc.LOGWARNING)
            return None

        c.title = data.get('name')
        if data.get('type') == 'pseudostreaming':
            m = M_STREAM
        else:
            m = M_BROWSE
        c.url = request_to_self({Q_MODE: m, Q_STREAMKEY: c.key})

        return c

    def listitem(self):
        """Create a Kodi listitem from the metadata"""

        li = xbmcgui.ListItem(self.title)
        art_dict = {'icon': self.icon, 'poster': self.icon, 'fanart': self.fanart}
        # Check if there's any art, setArt can be kinda slow
        if max(v for v in art_dict.values()):
            li.setArt(art_dict)
        li.setInfo('video', {'plot': self.description})

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
    def __init__(self, offset=None, duration=None, media_type='video', languages=None, publish_date=None,
                 size=None, is_folder=False, **kwargs):
        """An object containing metadata for a video or audio recording"""

        super(Media, self).__init__(**kwargs)
        self.offset = offset
        self.media_type = media_type
        self.size = size
        self.languages = languages
        if self.languages is None:
            self.languages = []
        self.__publish_date = publish_date
        self.__duration = duration
        self.is_folder = is_folder

    @classmethod
    def parse_media(cls, data, censor_hidden=True):
        """Constructor taking jw media metadata

        :param data: deserialized JSON data from jw.org
        :param censor_hidden: if True, media marked as hidden will ask for permission before being displayed
        """
        c = cls.parse_common(data)
        c.key = data.get('languageAgnosticNaturalKey')

        if c.hidden and censor_hidden:
            if not c.key:
                xbmc.log('hidden media has no "key" metadata, skipping', xbmc.LOGWARNING)
                return None
            hidden_item = cls(title=getstr(30013),
                              url=request_to_self({Q_MODE: M_HIDDEN, Q_MEDIAKEY: c.key}),
                              is_folder=True)
            return hidden_item

        c.url, c.size = c.get_preferred_media_file(data.get('files', []))
        if not c.url:
            xbmc.log('media has no playable files, skipping', xbmc.LOGWARNING)
            return None

        c.title = data.get('title')
        if data.get('type') == 'audio':
            c.media_type = 'music'
        c.duration = data.get('duration')
        c.publish_date = data.get('firstPublished')
        c.languages = data.get('availableLanguages', [])

        return c

    @classmethod
    def parse_hits(cls, data):
        """Create an instance of Media out of search results

        :param data: deserialized search result JSON data from jw.org
        """
        c = cls()

        if 'type:audio' in data.get('tags', []):
            c.media_type = 'music'
        c.title = data.get('displayTitle')
        c.key = data.get('languageAgnosticNaturalKey')
        if not c.key:
            xbmc.log('hidden media has no "key" metadata, skipping', xbmc.LOGWARNING)
            return None
        c.publish_date = data.get('firstPublishedDate')
        if c.key:
            c.url = request_to_self({Q_MODE: M_PLAY, Q_MEDIAKEY: c.key})

        for m in data.get('metadata', []):
            if m.get('key') == 'duration':
                c.duration = m.get('value')

        # TODO? We could try for pnr and cvr images too, but I'm too lazy, and no one cares about search anyway
        for i in data.get('images', []):
            if i.get('size') == 'md' and i.get('type') == 'sqr':
                c.icon = i.get('url')
            if i.get('size') == 'md' and i.get('type') == 'lsr':
                c.fanart = i.get('url')

        return c

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
        """Take an jw JSON array of files and metadata and return the most suitable like (url, size)"""

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
            if f.get('subtitled') is subtitles:
                rank += subtitles_matches_pref
            files.append((rank, f))
        files.sort()

        if len(files) > 0:
            # [-1] The file with the highest rank, [1] the filename, not the rank
            f = files[-1][1]
            return f['progressiveDownloadURL'], f['filesize']
        else:
            return None, None

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
            info_dict['date'] = time.strftime('%d.%m.%Y', self.publish_date)
            info_dict['year'] = time.strftime('%Y', self.publish_date)

        li = xbmcgui.ListItem(self.title)
        li.setArt(art_dict)
        li.setInfo(self.media_type, info_dict)

        if self.offset:
            li.setProperty('StartOffset', self.offset)
        if self.url:
            # For some reason needed by xbmcplugin.setResolvedUrl
            li.setProperty("isPlayable", "true")

        # Play in other language context menu
        if self.key:
            query = {Q_MODE: M_LANGUAGES, Q_MEDIAKEY: self.key}
            if self.languages:
                query[Q_LANGFILTER] = ' '.join(self.languages)
            # Note: Use RunPlugin instead of RunAddon, because an add-on assumes a folder view
            action = 'RunPlugin(' + request_to_self(query) + ')'
            li.addContextMenuItems([(getstr(30006), action)])

        return li


def getr(obj, keys, default=None, fail=False):
    """Recursive get function

    :param obj: list, dictionary or tuple
    :param keys: an iterable with indexes and keys (or tuples with indexes and keys)
    :param default: value to return if it fails'
    :param fail: used internally

    Example of keys: ['colors', ('red', 'green'), 2]
    Would match: ['colors']['red'][2] or ['colors']['green'][2]
    Keys are tested in order, and the first valid value is returned
    """
    this_level = keys[0]
    del keys[0]

    if type(this_level) != tuple:
        this_level = (this_level,)

    for key_try in this_level:
        try:
            new_obj = obj[key_try]
            if keys:
                # More levels, go deeper
                return getr(new_obj, keys, fail=True)
            else:
                # Last level, return value
                return new_obj
        except (TypeError, KeyError, IndexError):
            # Could not get value, try next
            continue

    if fail:
        # No keys existed for this level, return to parent
        raise KeyError
    else:
        # Everything failed, we return nicely
        return default


def get_json(url, nofail=False):
    """Fetch JSON data from an URL and return it as a Python object

    :param url: URL to open or a Request object
    :param nofail: ignore URLError if True"""

    try:
        if type(url) == str:
            xbmc.log('opening ' + url, xbmc.LOGINFO)
        elif isinstance(url, urllib2.Request):
            xbmc.log('opening ' + url.get_full_url(), xbmc.LOGINFO)
        data = urllib2.urlopen(url).read().decode('utf-8')
    except urllib2.URLError as e:
        if nofail:
            xbmc.log('{}: {}'.format(url, e.reason), xbmc.LOGWARNING)
            return None
        else:
            xbmc.log('{}: {}'.format(url, e.reason), xbmc.LOGERROR)
            xbmcgui.Dialog().notification(
                addon.getAddonInfo('name'),
                getstr(30009),
                icon=xbmcgui.NOTIFICATION_ERROR)
            # Don't raise an error, it will just generate another cryptic notification in Kodi
            exit()
    else:
        return json.loads(data)


def get_jwt_token(update=False):
    """Get temporary authentication token from memory, or jw.org"""

    token = addon.getSetting('jwt_token')
    if not token or update is True:
        xbmc.log('requesting new authentication token from tv.jw.org', xbmc.LOGINFO)
        url = 'https://tv.jw.org/tokens/web.jwt'
        token = urllib2.urlopen(url).read().decode('utf-8')
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
        d = Directory.parse_category(c)
        if d:
            d.fanart = default_fanart
            d.add_item_in_kodi()

    # Get "search" translation from internet - overkill but so cool
    # Try cache first, to speed up loading
    search_label = addon.getSetting('search_tr')
    if not search_label:
        data = get_json('https://data.jw-api.org/mediator/v1/translations/' + language, nofail=True)
        search_label = getr(data, ['translations', language, 'hdgSearch'], default='Search')
        addon.setSetting('search_tr', search_label)
    d = Directory(url=request_to_self({Q_MODE: M_SEARCH}), title=search_label, fanart=default_fanart,
                  icon='DefaultMusicSearch.png')
    d.add_item_in_kodi()

    xbmcplugin.endOfDirectory(addon_handle)


def sub_level_page(sub_level):
    """A sub-level page with either folders or playable media"""

    data = get_json('https://data.jw-api.org/mediator/v1/categories/' + language + '/' + sub_level + '?&detailed=1')
    data = data['category']

    # Enable more viewtypes
    if data.get('type') == 'ondemand':
        xbmcplugin.setContent(addon_handle, 'videos')

    if 'subcategories' in data:
        for sc in data['subcategories']:
            d = Directory.parse_category(sc)
            if d:
                d.add_item_in_kodi()
    if 'media' in data:
        for md in data['media']:
            m = Media.parse_media(md)
            if m:
                m.add_item_in_kodi()

    xbmcplugin.endOfDirectory(addon_handle)


def play_stream(key):
    """Generate a playlist out of the streaming schedule and start playing it"""

    # TODO add utcOffset= to the URL, but how do we determine the timezone?
    data = get_json('https://data.jw-api.org/mediator/v1/schedules/' + language + '/' + key)
    pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    pl.clear()
    offset = str(getr(data, ['category', 'position', 'time'], default=0))
    for md in data['category']['media']:
        media = Media.parse_media(md)
        if media:
            if offset:
                media.offset = offset
                offset = None
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

    selection = xbmcgui.Dialog().select(None, dialog_strings)
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
        query = urllib.urlencode({'q': search_string, 'lang': language, 'limit': 24})
        headers = {'Authorization': 'Bearer ' + get_jwt_token()}
        try:
            data = get_json(urllib2.Request(url + query, headers=headers), nofail=True)
        except urllib2.HTTPError as e:
            if e.code == 401:
                headers = {'Authorization': 'Bearer ' + get_jwt_token(True)}
                data = get_json(urllib2.Request(url + query, headers=headers))
            else:
                raise e

        for hd in data['hits']:
            media = Media.parse_hits(hd)
            if media:
                media.add_item_in_kodi()

        xbmcplugin.endOfDirectory(addon_handle)


def hidden_media_dialog(media_key):
    """Ask the user for permission, then create a folder with a single media entry"""

    dialog = xbmcgui.Dialog()
    if dialog.yesno(getstr(30013), getstr(30014)):
        url = 'https://data.jw-api.org/mediator/v1/media-items/' + language + '/' + media_key
        data = get_json(url)
        media = Media.parse_media(data['media'][0], censor_hidden=False)
        if media:
            media.add_item_in_kodi()
        else:
            raise RuntimeError
        xbmcplugin.endOfDirectory(addon_handle)


def resolve_media(media_key, lang=None):
    """Resolve to a playable URL for a media key name, as found in tv.jw.org URLs

    :param media_key: string, media to play
    :param lang: string, language code

    When language is specified, play video in that language, and save language in history
    """
    if lang:
        save_language_history(lang)

    url = 'https://data.jw-api.org/mediator/v1/media-items/' + (lang or language) + '/' + media_key
    data = get_json(url)
    media = Media.parse_media(data['media'][0], censor_hidden=False)
    if media:
        xbmcplugin.setResolvedUrl(addon_handle, succeeded=True, listitem=media.listitem_with_path())
    else:
        raise RuntimeError


def request_to_self(query):
    """Return a string with an URL request to the add-on itself"""

    return sys.argv[0] + '?' + urllib.urlencode(query)


def main():
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
    elif mode == M_BROWSE:
        sub_level_page(args[Q_CATKEY])
    elif mode == M_STREAM:
        play_stream(args[Q_STREAMKEY])
    # Backwards compatibility
    elif mode.startswith('Streaming') and mode != 'Streaming':
        play_stream(mode)
    else:
        sub_level_page(mode)


if __name__ == '__main__':
    main()
