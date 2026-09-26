from typing import Optional

from ._media import Media
from ._api_responses import FileDict, SubtitleDict, MediaDict
from ._file import File, Subtitles
from ._session_base import BaseSession


def resolution_from_label(label: str) -> int:
    try:
        # Example label: '360p'
        if label.lower().endswith('p'):
            return int(label[:-1])
        # Could this ever be? '4K' is 1080*2
        elif label.upper().endswith('K'):
            return int(label[:-1]) * 540
        else:
            return int(label)
    except (AttributeError, TypeError, ValueError):
        return 0


def create_media(d: MediaDict, *, parent: Optional[str], session: BaseSession) -> Media:
    files = [create_file(fd) for fd in d.get('files', [])]

    return Media(
        description=d.get('description', ''),
        duration=d.get('duration', 0.0),
        duration_HHMM=d.get('durationFormattedHHMM', '0:00'),
        duration_min_sec=d.get('durationFormattedMinSec', '0s'),
        files=files,
        guid=d.get('guid', ''),
        images=d.get('images', {}),
        key=d['languageAgnosticNaturalKey'],
        key_with_language=d['naturalKey'],
        languages=d.get('availableLanguages', []),
        parent=parent,
        primary_category_key=d.get('primaryCategory'),
        print_references=d.get('printReferences', []),
        published=d.get('firstPublished', '')[:19],  # YYYY-MM-DDTHH:MM:SS
        session=session,
        tags=d.get('tags', []),
        title=d.get('title', ''),
        type=d['type'],
    )


def create_file(d: FileDict) -> File:
    subtitle_data = d.get('subtitles')
    subtitles = create_subtitles(subtitle_data) if subtitle_data is not None else None

    return File(
        bitrate=d.get('bitRate', 0.0),
        checksum=d.get('checksum'),
        duration=d.get('duration', 0.0),
        frame_rate=d.get('frameRate', 0.0),
        height=d.get('frameHeight', 0),
        mimetype=d.get('mimetype', 'application/octet-stream'),
        modified=d.get('modifiedDatetime', '')[:19],  # YYYY-MM-DDTHH:MM:SS
        resolution=resolution_from_label(d.get('label', '')),
        size=d.get('filesize', 0),
        subtitles=subtitles,
        subtitled_hard=d.get('subtitled', False),
        url=d['progressiveDownloadURL'],
        width=d.get('frameWidth', 0),
    )


def create_subtitles(d: SubtitleDict) -> Subtitles:
    return Subtitles(
        checksum=d.get('checksum'),
        date=d.get('modifiedDatetime', '')[:19],  # YYYY-MM-DDTHH:MM:SS
        url=d['url'],
    )
