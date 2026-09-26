"""
(very untested) Wrapper for the jw.org publications API
"""
from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Optional
from urllib.error import HTTPError

from .._dictwrapper import _DictWrapper
from .._request import get_json as _get_json
from ..common import NotFoundError as _NotFoundErrorBase

TYPE_MP3 = 'MP3'
TYPE_PDF = 'PDF'
TYPE_EPUB = 'EPUB'
TYPE_JWPUB = 'JWPUB'
TYPE_RTF = 'RTF'

_API_BASE = 'https://b.jw-cdn.org/apis/pub-media/GETPUBMEDIALINKS'


class NotFoundError(_NotFoundErrorBase):
    """Raised when a publication/languge was not found"""
    ...


class Language(_DictWrapper):
    def __init__(self, code: str, data: dict):
        super().__init__(data)
        self.__code = code

    def __repr__(self):
        try:
            return f'<{self.__class__.__name__} {self.code!r}>'
        except Exception:
            return super().__repr__()

    @property
    def code(self):
        return self.__code

    @property
    def isocode(self) -> str:
        """ISO 639 language code

        Raises LookupError if undefined.
        """
        return self._get_string('locale')

    @property
    def name(self) -> str:
        """Display name"""
        return self._get_string('name', '')

    @property
    def rtl(self) -> bool:
        """Right to left"""
        return self.data.get('direction') == 'rtl'


class Marker(_DictWrapper):
    def __repr__(self):
        try:
            return f'<{self.__class__.__name__} {self.start}-{self.duration}>'
        except Exception:
            return super().__repr__()

    @property
    def duration(self):
        return _timestamp_to_float(self.data['duration'])

    @property
    def start(self):
        return _timestamp_to_float(self.data['startTime'])

    @property
    def verse(self) -> Optional[int]:
        return self.data.get('verseNumber')


class MarkerGroup(_DictWrapper):
    @property
    def bible_book_chapter(self) -> int:
        return self.data['bibleBookChapter']

    @property
    def bible_book_number(self) -> int:
        return self.data['bibleBookNumber']

    @property
    def hash(self) -> str:
        """TODO what type?"""
        return self.data['hash']

    @property
    def first_marker(self) -> Marker:
        """Marker of introduction"""
        return Marker(self.data['introduction'])

    # TODO Use of `functools.lru_cache` or `functools.cache` on methods can lead to memory leaks

    @property
    @lru_cache(maxsize=None)
    def markers(self) -> list[Marker]:
        """Generate Markers for each verse"""
        return [Marker(m) for m in self.data.get('markers', [])]

    @property
    def type(self) -> str:
        """May be 'publication' or 'bible' TODO what more?"""
        return self.data['type']

    @property
    def spoken_language(self) -> str:
        return self.data['mepsLanguageSpoken']

    @property
    def written_language(self) -> str:
        return self.data['mepsLanguageWritten']


class File(_DictWrapper):
    def __init__(self, language: str, filetype: str, data: dict):
        """
        :param language: JW language code
        :param filetype: File type like MP3
        """
        super().__init__(data)
        self.language = language
        self.type = filetype

    def __repr__(self):
        try:
            return f'<{self.__class__.__name__} {self.url.split("/")[-1]!r}>'
        except Exception:
            return super().__repr__()

    @property
    def bible_book(self) -> int:
        """Bible book, 0 = All, 1 = Genesis"""
        return self.data['booknum']

    @property
    def bit_rate(self) -> float:
        """TODO what unit?"""
        return self.data['bitRate']

    @property
    def checksum(self) -> str:
        return self.data['file']['checksum']

    @property
    def date(self) -> Optional[datetime]:
        """Modification date"""
        try:
            # Example 2019-01-20T10:28:27+00:00
            # TODO Naive datetime constructed using `datetime.datetime.strptime()` without %z
            return datetime.strptime(self.data['file']['modifiedDatetime'][:-6], '%y-%m-%dT%H:%M:%S')
        except (IndexError, KeyError, TypeError, ValueError):
            return None

    @property
    def doc_id(self) -> str:
        """May be used to load articles at jw.org TODO is this true?"""
        return self.data['docid']

    @property
    def duration(self) -> int:
        """Duration in seconds"""
        return self.data['duration']

    @property
    def edition_code(self) -> str:
        """TODO what?"""
        return self.data['edition']

    @property
    def edition_descr(self) -> str:
        """TODO what? Example: Regular"""
        return self.data['editionDescr']

    @property
    def frame_height(self) -> int:
        return self.data['frameHeight']

    @property
    def frame_rate(self) -> int:
        return self.data['frameRate']

    @property
    def frame_width(self) -> int:
        return self.data['frameWidth']

    @property
    def has_track(self) -> bool:
        return self.data['hasTrack']

    @property
    def image(self) -> Optional[str]:
        return self.data['trackImage']['url'] or None

    @property
    def label(self) -> str:
        """TODO is this like video quality? Example: 0p"""
        return self.data['label']

    @property
    def markers(self) -> Optional[MarkerGroup]:
        """MarkerCollection - holds list of Markers plus some metadata"""
        if not self.data.get('markers'):
            return None
        return MarkerGroup(self.data['markers'])

    @property
    def mimetype(self) -> str:
        return self.data['mimetype']

    @property
    def pub_code(self) -> str:
        return self.data['pub']

    @property
    def pub_format(self) -> str:
        """TODO what?"""
        return self.data['format']

    @property
    def pub_format_descr(self) -> str:
        """TODO what? Example: Regular"""
        return self.data['formatDescr']

    @property
    def size(self) -> int:
        """TODO what unit?"""
        return self.data['filesize']

    @property
    def specialty_code(self) -> str:
        """Example: BR2 (braille)"""
        return self.data['specialty']

    @property
    def specialty_descr(self) -> str:
        """Example: Braille Grade 2"""
        return self.data['specialtyDescr']

    @property
    def stream(self) -> str:
        """TODO What is this? Example: https://jw.org"""
        return self.data['file']['stream']

    @property
    def subtitled(self) -> bool:
        return self.data['subtitled']

    @property
    def title(self) -> str:
        return self.data['title']

    @property
    def track(self) -> int:
        """Track number (ie chapter number of book when dealing with audio recordings)"""
        return self.data['track']

    @property
    def url(self) -> str:
        """Download URL"""
        return self.data['file']['url']


class Publication(_DictWrapper):
    def __repr__(self):
        try:
            string = f'<{self.__class__.__name__} code={self.code!r}'

            if self.bible_book is not None:
                string += f' bible_book={self.bible_book!r}'
            if self.issue is not None:
                string += f' issue={self.issue!r}'
            if self.track is not None:
                string += f' track={self.track!r}'
            string += '>'
            return string
        except Exception:
            return super().__repr__()

    @property
    def bible_book(self) -> Optional[int]:
        """Number of bible book (0 is index page)"""
        return self.data.get('booknum') or None

    @property
    def code(self) -> str:
        """Publication code"""
        return self.data['pub']

    @property
    def date(self) -> str:
        """TODO Formatted date of some kind"""
        return self.data.get('formattedDate', '')

    @property
    def format(self) -> list:
        """TODO List of some kind of file formats"""
        return self.data['fileformat']

    @property
    def image(self) -> Optional[str]:
        return self.data.get('pubImage', {}).get('url')

    @property
    def issue(self) -> Optional[str]:
        """Magazine issue code"""
        return self.data.get('issue') or None

    @property
    @lru_cache(maxsize=None)
    def files(self) -> list[File]:
        """List of File info objects for all languages and file types"""
        return [File(lang, filetype, f)
                for lang in self.data.get('files', {})
                for filetype in self.data['files'][lang]
                for f in self.data['files'][lang][filetype]]

    @property
    @lru_cache(maxsize=None)
    def languages(self) -> list[Language]:
        """List of Language info"""
        return [Language(code, value) for code, value in self.data.get('languages', {}).items()]

    @property
    def name(self) -> str:
        return self.data['pubName']

    @property
    def parent_name(self) -> str:
        """Display name of parent publication"""
        return self.data['parentPubName']

    @property
    def speciality(self) -> str:
        """TODO Braille code etc?"""
        return self.data['speciality']

    @property
    def track(self) -> Optional[int]:
        """Track number (chapter of a book etc when dealing with sound recordings)"""
        return self.data.get('track')


def _timestamp_to_float(string: str) -> float:
    """Convert HH:MM:SS.nnn to float"""
    factor = 1
    result = 0.0
    for part in reversed(string.split(':')):
        result += float(part) * factor
        factor *= 60
    return result


def get_publication(pub: str,
                    lang: str,
                    *,
                    issue: Optional[int] = None,
                    bible_book: Optional[int] = None,
                    all_langs=False,
                    filetype: Optional[str] = None
                    ) -> Publication:
    query = {
        'output': 'json',
        'fileformat': filetype,
        'pub': pub,
        'issue': issue,
        'booknum': bible_book,
        'langwritten': lang,
        'txtCMSLang': lang,
        'alllangs': all_langs or None  # TODO check if this is needed
    }
    try:
        return _get_json(_API_BASE, query)
    except HTTPError as e:
        if e.code == 404:
            raise NotFoundError from e
        raise
