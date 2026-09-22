from __future__ import annotations

from typing import Iterable, List, NamedTuple

from resources.lib.jwapi import get_media, get_session
from resources.lib.jwlib.media import Language
from resources.lib.kodi import kodi
from resources.lib.requests import LanguageRequest, ConfigRequest, PlayRequest, ShuffleRequest
from resources.lib.settings import settings


def _filter_languages(languages: Iterable[Language], filter_codes: Iterable[str]) -> List[Language]:
    return list(filter(lambda lang: lang.code in filter_codes, languages))


def _sort_languages(languages: Iterable[Language]) -> List[Language]:
    # Put English first, followed by recent languages
    # (high score means bottom of the list, that's why we do inverse checks)
    recent = settings.language_history
    return sorted(languages, key=lambda lang: (
        lang.code != 'E',
        recent.index(lang.code) if lang.code in recent else len(recent),
    ))


def _format_language(language: Language) -> str:
    return '{} / {}'.format(language.name, language.vernacular)


def _build_query(request: LanguageRequest, lang: Language) -> str:
    if request.shuffle_category:
        return ShuffleRequest(category=request.shuffle_category, hidden=request.hidden, lang=lang.code).url
    elif request.play_media:
        return PlayRequest(media=request.play_media, hidden=request.hidden, lang=lang.code).url
    elif request.set_lang1:
        return ConfigRequest(lang1=lang.code, label=_format_language(lang)).url
    elif request.set_lang2:
        return ConfigRequest(lang2=lang.code, label=_format_language(lang)).url
    else:
        raise RuntimeError('invalid request, should not happen')


class _Action(NamedTuple):
    label: str
    command: str


def _build_actions(request: LanguageRequest, languages: List[Language]) -> List[_Action]:
    labels = [_format_language(lang) for lang in languages]
    queries = [_build_query(request, lang) for lang in languages]
    commands = ['RunPlugin(' + url + ')' for url in queries]

    return [_Action(labels[i], commands[i]) for i in range(len(labels))]


def langlist_endpoint(request: LanguageRequest) -> None:
    """API endpoint for a language menu that performs some action"""

    all_langs = get_session(hidden=False).get_languages()

    # TODO potential problem if some videos only exist in another language than English
    media = get_media(request.play_media, languages=['E'], hidden=request.hidden) if request.play_media else None

    filtered_langs = _filter_languages(all_langs, media.languages) if media else all_langs
    sorted_langs = _sort_languages(filtered_langs)

    actions = _build_actions(request, sorted_langs)

    selection = kodi().selection_dialog('', [action.label for action in actions])
    if selection >= 0:
        kodi().execute(actions[selection].command)
