import pytest


@pytest.mark.parametrize('build, version', [
    ('21.3 (21.3.0) Git:20260916-nogitfound', 21),
    ('20.0-RC1 (19.90.901) Git:20221230-abcdef', 20),
    ('19.4 (19.4.0) Git:20220305-aabbcc', 19),
    ('18.9 Git:20201023-0655c2c718', 18),
    ('22.0-ALPHA1 (21.90.700) Git:20250115-deadbeef', 22),
])
def test_get_major_version(kodi, build, version):
    kodi.fake_build_version = build

    assert kodi.get_major_version() == version


def test_get_major_version_default(kodi):
    assert kodi.get_major_version() == 21


@pytest.mark.parametrize('build', ['', 'unknown'])
def test_get_major_version_invalid(kodi, build):
    kodi.fake_build_version = build

    with pytest.raises(ValueError):
        kodi.get_major_version()
