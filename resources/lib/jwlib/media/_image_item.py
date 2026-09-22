from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Iterable

from ._api_responses import ImageDict
from .const import TAG_PREFER_SQUARE_IMAGES, RATIOS_16_9, RATIOS_SQUARE, SIZES_FROM_LARGEST


@dataclass
class ItemWithImages:
    images: ImageDict
    """Dictionary with image URLs

    See also `get_image()`.
    """

    tags: list[str]
    """List of tags, see `const.TAG_* <jwlib.media.const>`."""

    def get_image(self, ratios: Iterable[str] = (), sizes: Iterable[str] = ()) -> Optional[str]:
        """Return URL to first matching image.

        :param ratios: list of image ratios.
        :param sizes: list of image sizes.

        To select the desired image use one of `const.RATIOS_* <jwlib.media.const>` and `const.SIZES_* <jwlib.media.const>`.
        Alternatively hand pick ratios and sizes from `~jwlib.media.imagetable`.

        By default, return the largest 16:9 image, or 1:1 if the item is tagged `const.TAG_PREFER_SQUARE_IMAGES <jwlib.media.const>`.

        .. note::
            `Session.client_type` affects which images are available.
        """
        if not ratios:
            ratios = RATIOS_SQUARE if TAG_PREFER_SQUARE_IMAGES in self.tags else RATIOS_16_9
        if not sizes:
            sizes = SIZES_FROM_LARGEST

        for ratio in ratios:
            for size in sizes:
                url = self.images.get(ratio, {}).get(size)
                if url:
                    return url
        return None
