"""
Implementation of Kodi interface

This is the only place the xbmc modules should be imported.
"""
import logging
import sys
from functools import lru_cache
from typing import Union, Sequence

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

from resources.lib.kodi import ItemType, KodiInterface, ListItem, LogLevel

logger = logging.getLogger(__name__)


@lru_cache
def _get_version() -> int:
    return RealKodiInterface().get_major_version()


def _content_type_of_list(items: Sequence[ListItem]) -> str:
    """Determine plugin content type based on items in list"""
    if any(i.type is ItemType.VIDEO for i in items):
        return 'videos'
    elif any(i.type is ItemType.AUDIO for i in items):
        return 'songs'
    else:
        # Tested in Kodi 18: This will force a list view with no icons next to the text
        return 'files'


def _legacy_set_info_labels(li: xbmcgui.ListItem, source: ListItem) -> None:
    if source.type is ItemType.AUDIO:
        li.setInfo('music', {
            'comment': source.description,
            'duration': str(source.duration),
            'title': source.title,
            'year': source.date[:4],
        })
    elif source.type is ItemType.VIDEO:
        li.setInfo('video', {
            'duration': str(source.duration),
            'title': source.title,
            'plot': source.description,
            'premiered': source.date[:10],
        })
    elif source.type is ItemType.FOLDER:
        if source.description:
            # There is no info label for folders, but 'video' seems to work fine
            li.setInfo('video', {'plot': source.description})


def _set_info_labels(li: xbmcgui.ListItem, source: ListItem) -> None:
    if source.type is ItemType.AUDIO:
        music_tag: xbmc.InfoTagMusic = li.getMusicInfoTag()
        music_tag.setComment(source.description)
        music_tag.setDuration(source.duration)
        music_tag.setTitle(source.title)
        try:
            music_tag.setYear(int(source.date[:4]))
        except (TypeError, ValueError):
            pass
    elif source.type is ItemType.VIDEO:
        video_tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        video_tag.setDuration(source.duration)
        video_tag.setTitle(source.title)
        video_tag.setPlot(source.description)
        video_tag.setPremiered(source.date[:10])
    elif source.type is ItemType.FOLDER:
        if source.description:
            video_tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
            video_tag.setPlot(source.description)


def kodi_item(item: ListItem) -> xbmcgui.ListItem:
    """Convert adapter ListItem to native ListItem"""

    li = xbmcgui.ListItem(item.title)

    # All Kodi's setter functions can be kinda slow, so make sure we have a value before calling them

    if item.fanart or item.icon:
        li.setArt({
            'fanart': item.fanart or item.icon or '',
            'icon': item.icon or '',
            'poster': item.icon or '',
        })

    if item.menu:
        li.addContextMenuItems([(i[0], f'RunPlugin({i[1]})') for i in item.menu])

    if item.subtitles:
        li.setSubtitles(item.subtitles)

    # For some reason needed for list items that will open xbmcplugin.setResolvedUrl
    if item.type in (ItemType.AUDIO, ItemType.VIDEO):
        li.setProperty('isPlayable', 'true')

    if _get_version() < 20:
        _legacy_set_info_labels(li, source=item)
    else:
        _set_info_labels(li, source=item)

    return li


class RealKodiInterface(KodiInterface):
    #
    # Addon info
    #

    def get_addon_fanart(self) -> str:
        return xbmcaddon.Addon().getAddonInfo('fanart')

    def get_addon_id(self) -> str:
        # This could also be derived from sys.argv[0]
        # which is an URL, like plugin://plugin.video.jwb-unofficial/browse/
        return xbmcaddon.Addon().getAddonInfo('id')

    def get_addon_name(self) -> str:
        return xbmcaddon.Addon().getAddonInfo('name')

    def get_addon_path(self) -> str:
        return xbmcaddon.Addon().getAddonInfo('path')

    def get_addon_profile_dir(self) -> str:
        return xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))

    def get_addon_query(self) -> str:
        # Query like ?mode=play&media=ThisVideo
        return sys.argv[2]

    def get_addon_version(self) -> str:
        return xbmcaddon.Addon().getAddonInfo('version')

    def get_localized_string(self, id: int) -> str:
        return xbmcaddon.Addon().getLocalizedString(id)

    def get_setting(self, key: str) -> str:
        return xbmcaddon.Addon().getSetting(key)

    def get_setting_bool(self, key: str) -> bool:
        if _get_version() < 20:
            return self.get_setting(key) == 'true'
        else:
            return xbmcaddon.Addon().getSettingBool(key)

    def set_setting(self, key: str, value: str) -> None:
        logger.debug(f'Setting {key!r} => {value!r}')
        xbmcaddon.Addon().setSetting(key, value)

    def set_setting_bool(self, key: str, value: bool) -> None:
        if _get_version() < 20:
            self.set_setting(key, 'true' if value else 'false')
        else:
            logger.debug(f'Setting {key!r} => {value!r}')
            xbmcaddon.Addon().setSettingBool(key, value)

    #
    # Directory plugin
    #

    @property
    def handle(self) -> int:
        return int(sys.argv[1])

    def add_items(self, items: Sequence[ListItem]) -> None:
        # Enables richer list view alternatives if there's media
        xbmcplugin.setContent(self.handle, _content_type_of_list(items))

        xbmcplugin.addDirectoryItems(
            handle=self.handle,
            items=[(i.url, kodi_item(i), i.type is ItemType.FOLDER) for i in items],
            totalItems=len(items),
        )

        xbmcplugin.endOfDirectory(self.handle)

    def set_resolved_url(self, item: ListItem):
        li = kodi_item(item)
        # Apparently setPath() is slow, so we only use it here when a video is about to be played
        li.setPath(item.url)
        xbmcplugin.setResolvedUrl(self.handle, succeeded=True, listitem=li)

    #
    # GUI elements
    #

    def notify(self, heading: str, message: str) -> None:
        xbmcgui.Dialog().notification(heading, message, icon=xbmcgui.NOTIFICATION_ERROR)

    def input_dialog(self) -> str:
        kb = xbmc.Keyboard()
        kb.doModal()
        return kb.getText() if kb.isConfirmed() else ''

    def ok_dialog(self, title: str, message: str) -> bool:
        return xbmcgui.Dialog().ok(title, message)

    def question_dialog(self, title: str, message: str) -> bool:
        return xbmcgui.Dialog().yesno(title, message)

    def selection_dialog(self, title: str, items: Sequence[Union[str, ListItem]]) -> int:
        return xbmcgui.Dialog().select('', [kodi_item(i) if isinstance(i, ListItem) else i for i in items])

    def text_dialog(self, title: str, message: str) -> None:
        xbmcgui.Dialog().textviewer(title, message)

    #
    # Internals
    #

    def get_build_version(self) -> str:
        return xbmc.getInfoLabel('System.BuildVersion')

    def get_system_language(self) -> str:
        return xbmc.getLanguage(xbmc.ISO_639_1)

    def execute(self, command: str) -> None:
        xbmc.executebuiltin(command)

    _log_level_translation = {
        LogLevel.DEBUG: xbmc.LOGDEBUG,
        LogLevel.INFO: xbmc.LOGINFO,
        LogLevel.WARN: xbmc.LOGWARNING,
        LogLevel.ERROR: xbmc.LOGERROR,
        LogLevel.FATAL: xbmc.LOGFATAL,
    }

    def log(self, message: str, level: LogLevel = LogLevel.INFO) -> None:
        xbmc.log(message, self._log_level_translation[level])

    #
    # Player
    #

    def get_playing_file(self) -> str:
        return xbmc.Player().getPlayingFile()

    def show_subtitles(self, show: bool) -> None:
        xbmc.Player().showSubtitles(show)

    def start_playlist(self, items: Sequence[ListItem]):
        # Set playlist type (audio playlists does not open fullscreen)
        list_type = xbmc.PLAYLIST_VIDEO if any(i.type is ItemType.VIDEO for i in items) else xbmc.PLAYLIST_MUSIC

        pl = xbmc.PlayList(list_type)
        pl.clear()
        for item in items:
            pl.add(item.url, kodi_item(item))
        xbmc.Player().play(pl)
