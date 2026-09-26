from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import TypeVar, Optional, Iterable, TYPE_CHECKING, Union

from . import const
from ._file import File
from ._image_item import ItemWithImages
from ._iterator_compat import IteratorCompatibleList
from .._deprecated import deprecated

if TYPE_CHECKING:
    from ._category import Category
    from ._session_base import BaseSession

T = TypeVar('T')


@dataclass
class Media(ItemWithImages):
    """Information about a media item.

    Use `Session.get_media()`, `Category.get_media()` or `Media.create()` to create an instance.
    """

    description: str
    """Media description, seems to be empty for the most part."""

    duration: float
    """Duration in seconds."""

    duration_HHMM: str
    """Duration as a string, like ``2:16``."""

    duration_min_sec: str
    """Duration as a string, like ``2m 16s``."""

    files: list[File]
    """List of `File`."""

    guid: str
    """24 character long hexadecimal identifier."""

    key: str
    """Code name, language agnostic.

    This is the code that can be passed to `Session.get_media()`.
    """

    key_with_language: str
    """Code name, including language code.

    Looks similar to the filename, but not the same. Use case unknown.
    """

    languages: list[str]
    """List of languages in which this item is available."""

    parent: Optional[str]
    """Code name of the category that contained this item.

    This attribute does not come from the media itself, rather it's a reflection of the category tree traversal.
    It may be useful in some scenarios, since multiple categories may contain the "same" media item, and in those
    cases this is the only value that will differ.

    If the media item came from `Session.get_media()`, this will be `None`.

    See also `primary_category_key`.
    """

    primary_category_key: Optional[str]
    """Code name of the primary parent category.

    Unlike `parent`, this will always be the same, no matter where in the category tree a media item was taken from.
    It also works for media items returned by `Session.get_media()`.

    (In theory this should always be non-zero, but IRL it has been None for some items.)

    See also `get_primary_category()`.
    """

    published: str
    """Date when first published, as yyyy-mm-ddThh:mm:ss.

    See also `get_published()` and `const.TIME_FORMAT <jwlib.media.const>`.
    """

    print_references: list[str]
    """List of code names, similar to the ones you find printed in the literature.

    For example, a broadcasting may be called ``jwb-141-1``.

    AFAIK these code names are not used for any API requests.
    """

    session: BaseSession
    """Session, needed by `get_primary_category()`."""

    title: str
    """Display name."""

    type: const.MediaType
    """Media type, like ``audio`` or ``video``."""

    @staticmethod
    def create(*,
               description='',
               duration=0.0,
               duration_HHMM='0:00',
               duration_min_sec='0s',
               files: Optional[Iterable[Union[File, dict]]] = None,
               guid='',
               images: Optional[dict] = None,
               key='',
               key_with_language='',
               languages: Optional[Iterable[str]] = None,
               parent: Optional[str] = None,
               primary_category_key: Optional[str] = None,
               print_references: Optional[Iterable[str]] = None,
               published='',
               session: BaseSession,
               tags: Optional[Iterable[str]] = None,
               title='',
               type: const.MediaType = const.MEDIA_VIDEO,
               ) -> Media:
        return Media(
            description=description,
            duration=duration,
            duration_HHMM=duration_HHMM,
            duration_min_sec=duration_min_sec,
            files=[f if isinstance(f, File) else File.create(**f) for f in files or []],
            guid=guid,
            images=images if images is not None else {},
            key=key,
            key_with_language=key_with_language,
            languages=list(languages) if languages is not None else [],
            parent=parent,
            primary_category_key=primary_category_key,
            print_references=list(print_references) if print_references is not None else [],
            published=published,
            session=session,
            tags=list(tags) if tags is not None else [],
            title=title,
            type=type,
        )

    def __repr__(self):
        try:
            return f"<{self.__class__.__name__} '{self.session.language}/{self.key}'>"
        except Exception:
            return super().__repr__()

    @property
    @deprecated("Use `dataclasses.asdict()` instead.")
    def data(self) -> dict:
        return asdict(self)

    def get_file(self, *, resolution=0, subtitles=False) -> File:
        """Return the `File` that best matches these criteria.

        These are not hard limits - if there is no perfect match it will take the closest possible.

        :param resolution: max resolution (0 = no limit)
        :param subtitles: whether file should have subtitles (soft is preferred over hard)
        """

        try:
            if resolution == 0:
                resolution = max(f.resolution for f in self.files)

            return max(self.files, key=lambda f: (
                (f.resolution <= resolution),
                (f.subtitles is not None) == subtitles,
                f.subtitled_hard == subtitles,
                -abs(f.resolution - resolution)
            ))
        except ValueError as e:
            raise LookupError from e

    @deprecated("Use `Media.files` instead.")
    def get_files(self) -> Iterable[File]:
        return IteratorCompatibleList(self.files)

    def get_primary_category(self, *, include_media=False) -> Optional[Category]:
        """Return the primary parent category.

        If the category is not in the cache, a request will be sent to the server.

        :param include_media: see `Session.get_category()`

        See also `primary_category_key`.
        """
        if self.primary_category_key is None:
            return None
        return self.session.get_category(self.primary_category_key, include_media=include_media)

    def get_published(self) -> datetime:
        """Return `Media.published` as a `datetime`."""
        return datetime.strptime(self.published, const.TIME_FORMAT)

    @property
    def subtitle_url(self) -> Optional[str]:
        """Convenience method to get first available subtitle URL."""
        for file in self.files:
            if file.subtitles:
                return file.subtitles.url
        return None
