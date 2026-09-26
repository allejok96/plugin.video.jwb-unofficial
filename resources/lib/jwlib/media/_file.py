from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Union
from urllib.parse import urlparse

from . import const
from ._subtitles import Subtitles
from .._deprecated import deprecated


@dataclass
class File:
    """Information about a downloadable file."""

    bitrate: float
    """Bitrate in kb/s."""

    checksum: Optional[str]
    """MD5 checksum."""

    duration: float
    """Duration in seconds."""

    frame_rate: float
    """Frames per second."""

    height: int
    """Frame height."""

    mimetype: str
    """MIME type, like ``video/mp4``."""

    modified: str
    """Modification time, as yyyy-mm-ddThh:mm:ss

    See also `get_modified()` and `const.TIME_FORMAT <jwlib.media.const>`.
    """

    resolution: int
    """Video resolution.

    This is the human readable value and not the actual video height.
    Common values are 240, 360, 480, 720, 1080, or 0 if it's an audio file.
    """

    size: int
    """File size in bytes."""

    subtitles: Optional[Subtitles]
    """External soft subtitles"""

    subtitled_hard: bool
    """Has subtitles hardcoded in the video frame."""

    url: str
    """URL for downloading."""

    width: int
    """Frame width."""

    @staticmethod
    def create(*,
               bitrate=0.0,
               checksum: Optional[str] = None,
               duration=0.0,
               frame_rate=0.0,
               height=0,
               mimetype='application/octet-stream',
               modified='',
               resolution=0,
               size=0,
               subtitles: Union[Subtitles, dict, None] = None,
               subtitled_hard=False,
               url: str,
               width=0,
               ) -> File:
        if isinstance(subtitles, Subtitles):
            subtitles_instance = subtitles
        elif subtitles is not None:
            subtitles_instance = Subtitles.create(**subtitles)
        else:
            subtitles_instance = None
        return File(
            bitrate=bitrate,
            checksum=checksum,
            duration=duration,
            frame_rate=frame_rate,
            height=height,
            mimetype=mimetype,
            modified=modified,
            resolution=resolution,
            size=size,
            subtitles=subtitles_instance,
            subtitled_hard=subtitled_hard,
            url=url,
            width=width,
        )

    def __repr__(self):
        try:
            return f"<{self.__class__.__name__} {self.filename!r}>"
        except Exception:
            return super().__repr__()

    @property
    @deprecated("Use `dataclasses.asdict()` instead.")
    def data(self) -> dict:
        return asdict(self)

    @property
    def filename(self):
        """File name of downloadable file."""
        return os.path.basename(urlparse(self.url).path)

    def get_modified(self) -> datetime:
        """Return `File.modified` as a `datetime`."""
        return datetime.strptime(self.modified, const.TIME_FORMAT)

    @property
    @deprecated("Use `File.subtitles.checksum` instead.")
    def subtitle_checksum(self) -> Optional[str]:
        return self.subtitles.checksum if self.subtitles else None

    @property
    @deprecated("Use `File.subtitles.date` instead.")
    def subtitle_date(self) -> Optional[str]:
        return self.subtitles.date if self.subtitles else None

    @property
    @deprecated("Use `File.subtitles.url` instead.")
    def subtitle_url(self) -> Optional[str]:
        return self.subtitles.url if self.subtitles else None

    @property
    @deprecated("Check `File.subtitles` is not None instead.")
    def subtitled_soft(self) -> bool:
        return self.subtitles is not None
