# Licensed under the Apache License, Version 2.0
from __future__ import unicode_literals, division, print_function, absolute_import

import sys
import os.path
import json
import random
import time
import traceback

from kodi_six import xbmc, xbmcaddon, xbmcgui, xbmcplugin, py2_decode, py2_encode

from resources.lib.constants import Query as Q, Mode as M, SettingID, LocalizedStringID
from resources.lib.constants import CATEGORY_URL, LANGUAGE_URL, MEDIA_URL, SEARCH_URL, TOKEN_URL, TRANSLATION_URL

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


def log(msg, level=xbmc.LOGDEBUG):
    """Write to log file"""

    for line in msg.splitlines():
        xbmc.log(addon.getAddonInfo('id') + ': ' + line, level)


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

        if self.key:
            self.url = request_to_self({Q.MODE: M.BROWSE, Q.STREAMKEY: self.key})

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
        if any(art_dict.values()):
            li.setArt(art_dict)
        li.setInfo('video', {'plot': self.description})

        if self.streamable:
            query = {Q.MODE: M.STREAM, Q.STREAMKEY: self.key}
            action = 'RunPlugin(' + request_to_self(query) + ')'
            li.addContextMenuItems([(S.SHUFFLE_CAT, action)])

        return li

    def add_item_in_kodi(self):
        """Adds this as a directory item in Kodi"""

        xbmcplugin.addDirectoryItem(handle=addon_handle, url=self.url, listitem=self.listitem(),
                                    isFolder=self.is_folder)


class Media(Directory):
    def __init__(self, duration=None, media_type='video', publish_date=None,
                 size=None, is_folder=False, subtitles=None, **kwargs):
        """An object containing metadata for a video or audio recording"""

        super(Media, self).__init__(**kwargs)
        self.media_type = media_type
        self.size = size
        self.__publish_date = publish_date
        self.__duration = duration
        self.is_folder = is_folder
        self.subtitles = subtitles
        self.resolved_url = None

    def parse_media(self, data, censor_hidden=True):
        """Constructor taking jw media metadata

        :param data: deserialized JSON data from jw.org
        :param censor_hidden: if True, media marked as hidden will ask for permission before being displayed
        """
        self.parse_common(data)
        self.key = data.get('languageAgnosticNaturalKey')
        if self.key:
            self.url = request_to_self({Q.MODE: M.PLAY, Q.MEDIAKEY: self.key})

        if self.hidden and censor_hidden:
            # Reset to these values
            self.__init__(title=S.HIDDEN,
                          url=request_to_self({Q.MODE: M.HIDDEN, Q.MEDIAKEY: self.key}),
                          is_folder=True)
        else:
            self.resolved_url, self.size, self.subtitles = self.get_preferred_media_file(data.get('files', []))
            self.title = data.get('title')
            if data.get('type') == 'audio':
                self.media_type = 'music'
            self.duration = data.get('duration')
            self.publish_date = data.get('firstPublished')

    def parse_hits(self, data):
        """Create an instance of Media out of search results

        :param data: deserialized search result JSON data from jw.org
        """
        self.title = data.get('displayTitle')
        if 'type:audio' in data.get('tags', []):
            self.media_type = 'music'
            self.title += ' ' + S.AUDIO_ONLY
        self.key = data.get('languageAgnosticNaturalKey')
        self.publish_date = data.get('firstPublishedDate')
        if self.key:
            self.url = request_to_self({Q.MODE: M.PLAY, Q.MEDIAKEY: self.key})

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
        except (AttributeError, ValueError, TypeError):
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
            if f.get('subtitled') == subtitle_setting:
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

        # For some reason needed for listitems that will open xbmcplugin.setResolvedUrl
        li.setProperty('isPlayable', 'true')

        if self.subtitles:
            li.setSubtitles([self.subtitles])

        context_menu = []

        # Play in other language context menu
        if self.key:
            query = {Q.MODE: M.LANGUAGES, Q.MEDIAKEY: self.key}
            # Note: Use RunPlugin instead of RunAddon, because an add-on assumes a folder view
            action = 'RunPlugin(' + request_to_self(query) + ')'
            context_menu.append((S.PLAY_LANG, action))

        if context_menu:
            li.addContextMenuItems(context_menu)

        return li

    def listitem_with_resolved_url(self):
        """Return ListItem with path set, because apparently setPath() is slow"""

        li = self.listitem()
        li.setPath(self.resolved_url)
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


def get_json(url, ignore_errors=False, catch_401=True):
    """Fetch JSON data from an URL and return it as a Python object

    :param url: URL to open or a Request object
    :param ignore_errors: IO exceptions will only be logged, don't exit
    :param catch_401: If False HTTP 401 will be passed on instead of caught

    IF an IO exception occurs a message will be displayed and the script exits.
    """
    if isinstance(url, Request):
        log('opening {}'.format(url.get_full_url()), xbmc.LOGINFO)
    else:
        log('opening {}'.format(url), xbmc.LOGINFO)

    try:
        data = urlopen(url).read().decode('utf-8')  # urlopen returns bytes
    # Catches URLError, HTTPError, SSLError ...
    except IOError as e:
        if ignore_errors:
            log(traceback.format_exc(), level=xbmc.LOGWARNING)
            return None
        elif not catch_401 and isinstance(e, HTTPError) and e.code == 401:
            raise
        else:
            log(traceback.format_exc(), level=xbmc.LOGERROR)
            xbmcgui.Dialog().notification(
                addon.getAddonInfo('name'),
                S.CONN_ERR,
                icon=xbmcgui.NOTIFICATION_ERROR)
            # Don't raise an error, it will just generate another cryptic notification in Kodi
            exit()
            raise  # to make PyCharm happy

    return json.loads(data)


def top_level_page():
    """The main menu, media categories from tv.jw.org plus extra stuff"""

    default_fanart = os.path.join(addon.getAddonInfo('path'), addon.getAddonInfo('fanart'))

    if addon.getSetting(SettingID.START_WARNING) == 'true':
        dialog = xbmcgui.Dialog()
        try:
            dialog.textviewer(S.THEO_WARN, S.DISCLAIMER)  # Kodi v16
        except AttributeError:
            dialog.ok(S.THEO_WARN, S.DISCLAIMER)
        addon.setSetting(SettingID.START_WARNING, 'false')

    # Auto language
    isolang = xbmc.getLanguage(xbmc.ISO_639_1)
    if not addon.getSetting(SettingID.LANG_HIST):
        # Write English to language history, so this code only runs once
        addon.setSetting(SettingID.LANG_HIST, 'E')
        # If Kodi is in foreign language
        if isolang != 'en':
            data = get_json(LANGUAGE_URL + 'E/web')
            for l in data['languages']:
                if l['locale'] == isolang:
                    # Save setting, and update for this this instance
                    set_language(l['code'], l['name'] + ' / ' + l['vernacular'])
                    global global_lang
                    global_lang = addon.getSetting(SettingID.LANGUAGE) or 'E'
                    break

    data = get_json(CATEGORY_URL + global_lang + '?detailed=True')

    for c in data['categories']:
        d = Directory(fanart=default_fanart)
        d.parse_category(c)
        if d.url and not d.hidden:
            d.add_item_in_kodi()

    # Get "search" translation from internet - overkill but so cool
    # Try cache first, to speed up loading
    search_label = addon.getSetting(SettingID.SEARCH_TRANSL)
    if not search_label:
        data = get_json(TRANSLATION_URL + global_lang, ignore_errors=True)
        search_label = getitem(data, 'translations', global_lang, 'hdgSearch', default='Search')
        addon.setSetting(SettingID.SEARCH_TRANSL, search_label)
    d = Directory(url=request_to_self({Q.MODE: M.SEARCH}), title=search_label, fanart=default_fanart,
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
    data = get_json(CATEGORY_URL + global_lang + '/' + sub_level + '?&detailed=1')
    data = data['category']

    # Enable more viewtypes
    if data.get('type') == 'ondemand':
        xbmcplugin.setContent(addon_handle, 'videos')

    if 'subcategories' in data:
        for sc in data['subcategories']:
            d = Directory()
            d.parse_category(sc)
            if d.url and not d.hidden:
                d.add_item_in_kodi()
    if 'media' in data:
        for md in data['media']:
            m = Media()
            m.parse_media(md)
            if m.url:
                m.add_item_in_kodi()

    xbmcplugin.endOfDirectory(addon_handle)


def shuffle_category(key):
    """Generate a shuffled playlist and start playing"""

    data = get_json(CATEGORY_URL + global_lang + '/' + key + '?&detailed=1')
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
        if media.url and not media.hidden:
            pl.add(media.resolved_url, media.listitem())

    xbmc.Player().play(pl)


def language_dialog(media_key=None):
    """Display a list of languages and set the global language setting

    :param media_key: play this media file instead of changing global setting
    """
    # Note: the list from jw.org is already sorted by ['name']
    data = get_json(LANGUAGE_URL + global_lang + '/web')
    # Convert language data to a list of tuples with (code, name)
    languages = [(l.get('code'), l.get('name', '') + ' / ' + l.get('vernacular', ''))
                 for l in data['languages']]
    # Get the languages matching the ones from history and put them first
    history = addon.getSetting(SettingID.LANG_HIST).split()
    languages = [l for h in history for l in languages if l[0] == h] + languages

    if media_key:
        # Lookup media, and only show available languages
        url = MEDIA_URL + global_lang + '/' + media_key
        data = get_json(url)
        available_langs = data['media'][0].get('availableLanguages')
        if available_langs:
            languages = [l for l in languages if l[0] in available_langs]

    dialog_strings = []
    dialog_actions = []
    for code, name in languages:
        dialog_strings.append(name)
        if media_key:
            request = request_to_self({
                Q.MODE: M.PLAY,
                Q.MEDIAKEY: media_key,
                Q.LANGCODE: code})
            dialog_actions.append('RunPlugin(' + request + ')')
        else:
            request = request_to_self({
                Q.MODE: M.SET_LANG,
                Q.LANGNAME: name,
                Q.LANGCODE: code})
            dialog_actions.append('RunPlugin(' + request + ')')

    selection = xbmcgui.Dialog().select('', dialog_strings)
    if selection >= 0:
        xbmc.executebuiltin(dialog_actions[selection])


def set_language(lang, name):
    """Save a language to setting and history"""

    addon.setSetting(SettingID.LANGUAGE, lang)
    addon.setSetting(SettingID.LANG_NAME, name)
    save_language_history(lang)
    # Forget about the translation of "Search"
    addon.setSetting(SettingID.SEARCH_TRANSL, '')


def save_language_history(lang):
    """Save a language code first in history"""

    history = addon.getSetting(SettingID.LANG_HIST).split()
    history = [lang] + [h for h in history if h != lang]
    history = history[0:5]
    addon.setSetting(SettingID.LANG_HIST, ' '.join(history))


def search_page():
    """Display a search dialog, then the results"""

    kb = xbmc.Keyboard()
    kb.doModal()
    if kb.isConfirmed():
        # Enable more viewtypes
        xbmcplugin.setContent(addon_handle, 'videos')

        search_string = kb.getText()
        query = urlencode({'q': search_string, 'lang': global_lang, 'limit': 24})

        try:
            token = addon.getSetting(SettingID.TOKEN)
            if not token:
                raise RuntimeError

            headers = {'Authorization': 'Bearer ' + token}
            data = get_json(Request(SEARCH_URL + '?' + query, headers=headers), catch_401=False)

        except (HTTPError, RuntimeError):
            # Get and save new token
            log('requesting new authentication token from jw.org', xbmc.LOGINFO)
            token = urlopen(TOKEN_URL).read().decode('utf-8')
            if not token:
                raise RuntimeError('failed to get search authentication token')

            addon.setSetting(SettingID.TOKEN, token)

            headers = {'Authorization': 'Bearer ' + token}
            data = get_json(Request(SEARCH_URL + '?' + query, headers=headers))

        for hd in data['hits']:
            media = Media()
            media.parse_hits(hd)
            if media.url:
                media.add_item_in_kodi()

        xbmcplugin.endOfDirectory(addon_handle)


def hidden_media_dialog(media_key):
    """Ask the user for permission, then create a folder with a single media entry"""

    dialog = xbmcgui.Dialog()
    if dialog.yesno(S.HIDDEN, S.CONV_QUESTION):
        data = get_json(MEDIA_URL + global_lang + '/' + media_key)
        media = Media()
        media.parse_media(data['media'][0], censor_hidden=False)
        if media.url:
            media.add_item_in_kodi()
        else:
            raise RuntimeError
        xbmcplugin.endOfDirectory(addon_handle)


def resolve_media(media_key, lang=None):
    """Resolve to a playable URL for a media key name

    :param media_key: string, id of media to play
    :param lang: string, language code

    When language is specified, play video in that language, with subtitles in "global language"
    """
    if lang:
        # If we were called with a language, remove it from the URI and make a new request
        # This will make watched status and resume position language agnostic
        save_language_history(lang)
        addon.setSetting(SettingID.LANG_NEXT, lang)
        xbmc.executebuiltin('PlayMedia({}, resume)'.format(request_to_self({Q.MODE: M.PLAY, Q.MEDIAKEY: media_key})))
        return

    one_time_lang = addon.getSetting(SettingID.LANG_NEXT)

    data = get_json(MEDIA_URL + (lang or one_time_lang or global_lang) + '/' + media_key)
    media = Media()
    media.parse_media(data['media'][0], censor_hidden=False)

    if one_time_lang:
        if addon.getSetting(SettingID.REMEMBER_LANG) == 'false':
            addon.setSetting(SettingID.LANG_NEXT, None)

        if one_time_lang != global_lang:
            # Add subtitles from the global language too
            data = get_json(MEDIA_URL + global_lang + '/' + media_key, ignore_errors=True)
            global_lang_subs = getitem(data, 'media', 0, 'files', 0, 'subtitles', 'url', default=None)
            if global_lang_subs:
                media.subtitles = global_lang_subs

    if media.resolved_url:
        xbmcplugin.setResolvedUrl(addon_handle, succeeded=True, listitem=media.listitem_with_resolved_url())
        # Ugly way to turn on/off subtitles (without changing the global Kodi setting), try it for 10 sec
        # TODO change this if made possible in the future
        player = xbmc.Player()
        for i in range(1, 10):
            if player.getAvailableSubtitleStreams():
                # Subtitles are always on if a FOREIGN language is explicitly specified
                player.showSubtitles(one_time_lang and one_time_lang != global_lang or subtitle_setting)
                break
            time.sleep(1)

    else:
        raise RuntimeError


def request_to_self(query):
    """Return a string with an URL request to the add-on itself"""

    # argv[0] is path to the plugin
    return sys.argv[0] + '?' + urlencode(query)


if __name__ == '__main__':
    # To send stuff to the screen
    addon_handle = int(sys.argv[1])
    # To get settings and info
    addon = xbmcaddon.Addon()
    # For logging purpose
    addon_id = addon.getAddonInfo('id')
    # To to get translated strings
    S = LocalizedStringID(addon.getLocalizedString)

    video_res = [1080, 720, 480, 360, 240][int(addon.getSetting(SettingID.RESOLUTION))]
    subtitle_setting = addon.getSetting(SettingID.SUBTITLES) == 'true'
    global_lang = addon.getSetting(SettingID.LANGUAGE) or 'E'

    # The awkward way Kodi passes arguments to the add-on...
    # argv[2] is a URL query string, probably passed by request_to_self()
    # example: ?mode=play&media=ThisVideo
    args = parse_qs(sys.argv[2][1:])
    # parse_qs puts the values in a list, so we grab the first value for each key
    args = {k: v[0] for k, v in args.items()}

    # Tested in Kodi 18: This will disable all viewtypes but list and icons won't be displayed within the list
    xbmcplugin.setContent(addon_handle, 'files')

    mode = args.get(Q.MODE)

    if mode is None:
        top_level_page()
    elif mode == M.LANGUAGES:
        language_dialog(args.get(Q.MEDIAKEY))
    elif mode == M.SET_LANG:
        set_language(args[Q.LANGCODE], args[Q.LANGNAME])
    elif mode == M.HIDDEN:
        hidden_media_dialog(args[Q.MEDIAKEY])
    elif mode == M.SEARCH:
        search_page()
    elif mode == M.PLAY:
        resolve_media(args[Q.MEDIAKEY], args.get(Q.LANGCODE))
    elif mode == M.BROWSE:
        sub_level_page(args[Q.CATKEY])
    elif mode == M.STREAM:
        shuffle_category(args[Q.STREAMKEY])
    # Backwards compatibility
    elif mode.startswith('Streaming') and mode != 'Streaming':
        shuffle_category(mode)
    else:
        sub_level_page(mode)
