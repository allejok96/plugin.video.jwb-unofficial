from __future__ import annotations

from typing import TypedDict, Optional, Dict

from . import const
from ..common import NotFoundError as _NotFoundErrorBase


# ------
# Errors
# ------


class NotFoundError(_NotFoundErrorBase):
    """Raised when a category, media item or language was not found."""
    # The base class is for backwards compatibility


# ---------------------
# Media related classes
# ---------------------

ImageDict = Dict[str, Dict[str, str]]


class SubtitleDict(TypedDict):
    checksum: str
    modifiedDatetime: str
    url: str


class FileDict(TypedDict):
    bitRate: float
    checksum: str
    duration: float
    filesize: int
    frameHeight: int
    frameRate: float
    frameWidth: int
    label: str
    mimetype: str
    modifiedDatetime: str
    progressiveDownloadURL: str
    subtitled: bool
    subtitles: SubtitleDict  # omitted if there are none


class MediaDict(TypedDict):
    availableLanguages: list[str]
    description: str
    duration: float
    durationFormattedHHMM: str
    durationFormattedMinSec: str
    files: list[FileDict]
    firstPublished: str
    guid: str
    images: ImageDict
    languageAgnosticNaturalKey: str
    naturalKey: str
    primaryCategory: Optional[str]
    printReferences: list[str]
    tags: list[str]
    title: str
    type: const.MediaType


# -------------------------------------------
# Category with varying levels of information
# -------------------------------------------

class BasicCategoryDict(TypedDict):
    """Used by parentCategory"""
    description: str
    images: ImageDict
    key: str
    name: str
    tags: list[str]
    type: const.CategoryType


class PartialCategoryDict(BasicCategoryDict):
    """Used by subcategories"""
    media: list[MediaDict]  # omitted if type != ondemand


class CompleteCategoryDict(PartialCategoryDict):
    parentCategory: Optional[BasicCategoryDict]  # omitted on top-level categories
    subcategories: list[PartialCategoryDict]  # omitted if type != container


# -------------
# Language list
# -------------

class LanguageDict(TypedDict):
    code: str
    locale: str
    name: str
    pair: bool  # seems to always be False
    isRTL: bool
    script: str
    isSignLanguage: bool
    vernacular: str


# ------------------------------------------
# Pagination for Categories with media items
# ------------------------------------------

class Pagination(TypedDict):
    limit: int
    offset: int
    totalCount: int


# ----------------------
# Complete API responses
# ----------------------

class CategoryResponse(TypedDict):
    category: CompleteCategoryDict
    pagination: Pagination  # omitted if type != ondemand


class LanguageResponse(TypedDict):
    languages: list[LanguageDict]


class MediaResponse(TypedDict):
    # It seems to return HTTP 200 with a response of [] if the item doesn't exist...
    media: list[MediaDict]


class RootResponse(TypedDict):
    categories: list[CompleteCategoryDict]


class TranslationResponse(TypedDict):
    translations: dict[str, dict[str, str]]
