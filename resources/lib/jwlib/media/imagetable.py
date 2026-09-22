"""
The values from the table can be fed into `Category.get_image() <jwlib.media.Category.get_image>`
or `Media.get_image() <jwlib.media.Media.get_image>`.

.. rubric:: Category images

+---------+--------------+---------------+--------------+-----------------------------+
| ratio   | dimensions   | ratio alias   | size alias   | available for client type   |
+=========+==============+===============+==============+=============================+
| 1:1     | 50x50        | sqs           | xs           | none, roku                  |
+---------+--------------+---------------+--------------+-----------------------------+
| 1:1     | 75x75        | sqs           | sm           | none, roku                  |
+---------+--------------+---------------+--------------+-----------------------------+
| 1:1     | 100x100      | sqr           | xs           | none, roku                  |
+---------+--------------+---------------+--------------+-----------------------------+
| 1:1     | 120x120      | sqr           | sm           | none, roku                  |
+---------+--------------+---------------+--------------+-----------------------------+
| 1:1     | 125x125      | sqs           | md           | none                        |
+---------+--------------+---------------+--------------+-----------------------------+
| 1:1     | 200x200      | sqs           | lg           | none                        |
+---------+--------------+---------------+--------------+-----------------------------+
| 1:1     | 224x224      | sqr           | md           | none, roku                  |
+---------+--------------+---------------+--------------+-----------------------------+
| 1:1     | 342x342      | sqr           | lg           | none, roku                  |
+---------+--------------+---------------+--------------+-----------------------------+
| 1:1     | 600x600      | sqr           | xl           | none                        |
+---------+--------------+---------------+--------------+-----------------------------+
| 269:152 | 269x152      | wsr           | xs           | none, roku                  |
+---------+--------------+---------------+--------------+-----------------------------+
| 16:9    | 160x90       | wss           | xs           | none, roku                  |
+---------+--------------+---------------+--------------+-----------------------------+
| 16:9    | 320x180      | wss           | sm           | firetv, none, roku, www     |
+---------+--------------+---------------+--------------+-----------------------------+
| 16:9    | 640x360      | wss           | lg           | appletv, none               |
+---------+--------------+---------------+--------------+-----------------------------+
| 16:9    | 640x360      | wsr           | sm           | none, roku                  |
+---------+--------------+---------------+--------------+-----------------------------+
| 16:9    | 720x405      | wsr           | md           | none                        |
+---------+--------------+---------------+--------------+-----------------------------+
| 16:9    | 1280x720     | wsr           | lg           | none, roku                  |
+---------+--------------+---------------+--------------+-----------------------------+
| 3:1     | 240x80       | pnr           | xs           | none, roku                  |
+---------+--------------+---------------+--------------+-----------------------------+
| 3:1     | 480x160      | pnr           | sm           | none, roku                  |
+---------+--------------+---------------+--------------+-----------------------------+
| 3:1     | 801x267      | pnr           | md           | none, roku                  |
+---------+--------------+---------------+--------------+-----------------------------+
| 3:1     | 1200x400     | pnr           | lg           | appletv, none, roku, www    |
+---------+--------------+---------------+--------------+-----------------------------+

.. rubric:: Media images

+---------+--------------+---------------+--------------+----------------------------------+
| ratio   | dimensions   | ratio alias   | size alias   | available for client type        |
+=========+==============+===============+==============+==================================+
| 1:1     | 50x50        | sqs           | xs           | roku                             |
+---------+--------------+---------------+--------------+----------------------------------+
| 1:1     | 100x100      | sqr           | xs           | roku                             |
+---------+--------------+---------------+--------------+----------------------------------+
| 1:1     | 120x120      | sqr           | sm           | roku                             |
+---------+--------------+---------------+--------------+----------------------------------+
| 1:1     | 160x160      | cvr           | xs           | roku                             |
+---------+--------------+---------------+--------------+----------------------------------+
| 1:1     | 224x224      | sqr           | md           | appletv, none, roku              |
+---------+--------------+---------------+--------------+----------------------------------+
| 1:1     | 342x342      | sqr           | lg           | firetv, roku, www                |
+---------+--------------+---------------+--------------+----------------------------------+
| 269:152 | 269x152      | wsr           | xs           | roku                             |
+---------+--------------+---------------+--------------+----------------------------------+
| 16:9    | 160x90       | wss           | xs           | roku                             |
+---------+--------------+---------------+--------------+----------------------------------+
| 16:9    | 320x180      | wss           | sm           | appletv, none, roku, www         |
+---------+--------------+---------------+--------------+----------------------------------+
| 16:9    | 640x360      | wss           | lg           | appletv, firetv, none, www       |
+---------+--------------+---------------+--------------+----------------------------------+
| 16:9    | 640x360      | wsr           | sm           | roku                             |
+---------+--------------+---------------+--------------+----------------------------------+
| 16:9    | 1280x720     | wsr           | lg           | roku                             |
+---------+--------------+---------------+--------------+----------------------------------+
| 2:1     | 760x380      | lss           | lg           | www                              |
+---------+--------------+---------------+--------------+----------------------------------+
| 2:1     | 1200x600     | lsr           | xl           | none, www                        |
+---------+--------------+---------------+--------------+----------------------------------+
| 3:1     | 240x80       | pnr           | xs           | roku                             |
+---------+--------------+---------------+--------------+----------------------------------+
| 3:1     | 480x160      | pnr           | sm           | roku                             |
+---------+--------------+---------------+--------------+----------------------------------+
| 3:1     | 801x267      | pnr           | md           | roku                             |
+---------+--------------+---------------+--------------+----------------------------------+
| 3:1     | 1200x400     | pnr           | lg           | appletv, firetv, none, roku, www |
+---------+--------------+---------------+--------------+----------------------------------+

You can generate an up-to-date version by running::

    python -m jwlib.media.imagetable [CLIENT_TYPE] ...

.. note::
    This requires `Pillow` and `tabulate` to be installed.
"""
import sys
from fractions import Fraction
from typing import Dict, NamedTuple, Set
from urllib.request import urlopen

from .const import CLIENT_APPLETV, CLIENT_FIRETV, CLIENT_NONE, CLIENT_ROKU, CLIENT_WWW
from ._session_impl import Session

__all__ = (
    'generate_image_table',
)


def generate_image_table(*client_types: str) -> None:
    # We import these here so Sphinx doesn't need to install them
    # to generate the documentation
    from PIL import Image
    from tabulate import tabulate

    if not client_types:
        client_types = CLIENT_NONE, CLIENT_APPLETV, CLIENT_FIRETV, CLIENT_ROKU, CLIENT_WWW

    class ImageType(NamedTuple):
        ratio_alias: str
        size_alias: str

    class ClientsWhereImageTypeIsAvailable(Set[str]):
        def __str__(self):
            return ', '.join(sorted(self))

    ClientAvailabilityMap = Dict[ImageType, ClientsWhereImageTypeIsAvailable]

    class Dimensions(NamedTuple):
        x: int
        y: int

        @classmethod
        def from_url(cls, url):
            print(url)
            with urlopen(url) as response:
                x, y = Image.open(response).size
                return cls(x, y)

        def __str__(self):
            return f'{self.x}x{self.y}'

        def as_fraction(self):
            return Fraction(self.x, self.y)

        def formatted_ratio(self):
            fraction = self.as_fraction()
            return f'{fraction.numerator}:{fraction.denominator}'

    dimension_map: Dict[ImageType, Dimensions] = {}
    category_image_availability: ClientAvailabilityMap = {}
    media_image_availability: ClientAvailabilityMap = {}

    def parse_images(images: dict, availability_map: ClientAvailabilityMap, client: str) -> None:
        for ratio_alias in images:
            for size_alias in images[ratio_alias]:
                url = images[ratio_alias][size_alias]
                if not url:
                    continue
                image_type = ImageType(ratio_alias, size_alias)
                if image_type not in dimension_map:
                    dimension_map[image_type] = Dimensions.from_url(url)
                if image_type not in availability_map:
                    availability_map[image_type] = ClientsWhereImageTypeIsAvailable()
                availability_map[image_type].add(client)

    for client_name in client_types:
        session = Session(client_type=client_name)

        cat = session.get_category('VODStudio')
        parse_images(cat.images, category_image_availability, client_name)

        media = cat.get_subcategories()[0].get_media()[0]
        parse_images(media.images, media_image_availability, client_name)

    headers = ['ratio', 'dimensions', 'ratio alias', 'size alias', 'available for client type']

    class Row(NamedTuple):
        formatted_ratio: str
        dimensions: Dimensions
        ratio_alias: str
        size_alias: str
        clients: ClientsWhereImageTypeIsAvailable

    def create_rows(availability_map: ClientAvailabilityMap):
        for image_type, available_clients in availability_map.items():
            dimensions = dimension_map[image_type]
            yield Row(
                formatted_ratio=dimensions.formatted_ratio(),
                dimensions=dimensions,
                ratio_alias=image_type.ratio_alias,
                size_alias=image_type.size_alias,
                clients=available_clients
            )

    def row_sort_function(row: Row):
        return row.dimensions.as_fraction(), row.dimensions

    print('\n.. rubric:: Category images')
    rows_category = sorted(create_rows(category_image_availability), key=row_sort_function)
    print(tabulate(rows_category, headers=headers, tablefmt='grid'))

    print('\n.. rubric:: Media images')
    rows_media = sorted(create_rows(media_image_availability), key=row_sort_function)
    print(tabulate(rows_media, headers=headers, tablefmt='grid'))


if __name__ == '__main__':
    generate_image_table(*sys.argv[1:])
