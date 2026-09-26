from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from . import const


@dataclass
class Subtitles:
    """Information about soft subtitles."""

    url: str

    checksum: Optional[str]
    """MD5 checksum."""

    date: str
    """Modification time, as yyyy-mm-ddThh:mm:ss

    See also `get_date()` and `const.TIME_FORMAT <jwlib.media.const>`.
    """

    @staticmethod
    def create(*,
               checksum: Optional[str] = None,
               date='',
               url: str,
               ) -> Subtitles:
        return Subtitles(
            checksum=checksum,
            date=date,
            url=url,
        )

    def get_date(self) -> datetime:
        """Return `Subtitle.date` as a `datetime`."""
        return datetime.strptime(self.date, const.TIME_FORMAT)
