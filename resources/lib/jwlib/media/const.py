"""
Constants used in the mediator API
"""
from typing import Literal

# General
# =======

# Category.key of the root category.
# This is not part of the jw.org API, it is made up by jwlib.
ROOT_CATEGORY = 'All'

# Time format used by the API, can be passed to time.strptime()
TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'

# Client type
# ===========
# These can be passed to get_session().
# They affect what data will be made available.

CLIENT_APPLETV = 'appletv'
CLIENT_FIRETV = 'firetv'  # Default in jwlib.
CLIENT_JWORG = 'JWORG'
CLIENT_NONE = 'none'  # Includes obscure categories and convention releases (slow).
CLIENT_ROKU = 'roku'
CLIENT_RWLS = 'rwls'
CLIENT_SATELLITE = 'satellite'
CLIENT_WWW = 'www'  # Used by jw.org.


# Category type
# =============
CategoryType = Literal['container', 'ondemand']
CATEGORY_CONTAINER: CategoryType = 'container'
CATEGORY_ONDEMAND: CategoryType = 'ondemand'

# Media type
# ==========
MediaType = Literal['audio', 'video']
MEDIA_AUDIO: MediaType = 'audio'
MEDIA_VIDEO: MediaType = 'video'

# Image selection
# ===============
# These can be passed to get_image().
# Ratios are sorted from large-ish to small-ish.

RATIOS_SQUARE = ('sqr', 'sqs', 'cvr')
RATIOS_16_9 = ('wsr', 'wss')
RATIOS_2_1 = ('lsr', 'lss')
RATIOS_3_1 = ('pnr',)

SIZES_FROM_SMALLEST = ('xs', 'sm', 'md', 'lg', 'xl')
SIZES_FROM_LARGEST = tuple(reversed(SIZES_FROM_SMALLEST))

# Tags
# ====
# These are found in Category.tags or Media.tags.

# Used by jw.org for subcategories with a Play button.
TAG_ALLOW_PLAY_ALL_AS_ICONS_IN_GRID = 'AllowPlayAllAsIconsInGrid'
TAG_ALLOW_PLAY_ALL_IN_CATEGORY_HEADER = 'AllowPlayAllInCategoryHeader'

# Used by jw.org for subcategories with a Shuffle button.
TAG_ALLOW_SHUFFLE_AS_ICONS_IN_GRID = 'AllowShuffleAsIconsInGrid'
TAG_ALLOW_SHUFFLE_IN_CATEGORY_HEADER = 'AllowShuffleInCategoryHeader'

# Convention release media item (excluded automatically by many client types).
TAG_CONVENTION_RELEASE = 'ConventionRelease'

# Note:
# You normally don't have to check for the EXCLUDE tags.
# For example, if your client type is CLIENT_APPLETV it will automatically
# exclude items tagged TAG_EXCLUDE_APPLETV.

TAG_EXCLUDE_ALL_VIDEOS = 'AllVideosExclude'
TAG_EXCLUDE_APPLETV = 'AppleTVExclude'
TAG_EXCLUDE_FIRETV = 'FireTVExclude'
TAG_EXCLUDE_FROM_BREADCRUMBS = 'ExcludeFromBreadcrumbs'
TAG_EXCLUDE_JWL = 'JWLExclude'
TAG_EXCLUDE_JWL_CATALOG = 'JWLCatalogExclude'
TAG_EXCLUDE_JWORG = 'JWORGExclude'
TAG_EXCLUDE_LATEST = 'LatestVideosExclude'
TAG_EXCLUDE_LIBRARY = 'LibraryVideosExclude'
TAG_EXCLUDE_ROKU = 'RokuExclude'
TAG_EXCLUDE_RWLS = 'RWLSExclude'
TAG_EXCLUDE_SATELLITE = 'SatelliteExclude'
TAG_EXCLUDE_SEARCH = 'SearchExclude'
TAG_EXCLUDE_WEB = 'WebExclude'
TAG_EXCLUDE_WWW = 'WWWExclude'
TAG_EXCLUDE_WWW_CAT_LIST = 'WWWCatListExclude'

# Used by StudioFeatured.
TAG_FEATURED = 'WebFeatured'

TAG_INCLUDE_IN_JWORG_ALL_VIDEOS_CAT_LIST = 'IncludeInJWORGAllVideosCatList'

TAG_INCLUDE_SUB_CATEGORIES_NAV_RWLS = 'RWLSIncludeSubCategoriesAsNav'
TAG_INCLUDE_SUB_CATEGORIES_NAV_WEB = 'WebIncludeSubCategoriesInNav'
TAG_INCLUDE_SUB_CATEGORIES_NAV_WWW = 'WWWIncludeSubCategoriesAsNav'

TAG_PNR_FEATURED_LAYOUT = 'PNRFeaturedLayout'

# Used by audio categories, since the album covers are square.
TAG_PREFER_SQUARE_IMAGES = 'PreferSquareImages'

TAG_ROKU_CATEGORY_CAROUSEL_LIST = 'RokuCategoryCarouselList'
TAG_ROKU_CATEGORY_GRID = 'RokuCategoryGrid'
TAG_ROKU_CATEGORY_GRID_SCREEN = 'RokuCategoryGridScreen'
TAG_ROKU_CATEGORY_SELECTION_POSTER_SCREEN = 'RokuCategorySelectionPosterScreen'
TAG_ROKU_GRID_STYLE_SQUARE = 'RokuGridStyleSquare'
TAG_ROKU_MEDIA_ITEM_LIST_SCREEN = 'RokuMediaItemListScreen'

# Used by jw.org for main categories with a Shuffle button.
TAG_STREAM_THIS_CHANNEL_ENABLED = 'StreamThisChannelEnabled'

TAG_SUPPRESS_TOP_CATEGORY_BANNER = 'SuppressTopCategoryBanner'

# Limit number of items in the list.
TAGS_ITEM_LIMIT = (
    'LimitToZero',
    'LimitToOne',  # Used by FeaturedLibraryVideos.
    'LimitToTwo',  # Used by StudioFeatured.
    'LimitToThree',
    'LimitToFour',
    'LimitToFive',  # Used by FeaturedSetTopBoxes.
    'LimitToSix',
    'LimitToSeven',
    'LimitToEight',
    'LimitToNine',
    'LimitToTen',
)

# Month of release.
TAGS_MONTH = (
    'Month01',
    'Month02',
    'Month03',
    'Month04',
    'Month05',
    'Month06',
    'Month07',
    'Month08',
    'Month09',
    'Month10',
    'Month11',
    'Month12')
