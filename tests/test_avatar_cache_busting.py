"""Issue #259: the avatar must appear immediately after an upload.

The member_avatar response carries cache_expires=300, and the image
URL used to be constant per member — so browsers kept serving the
old pixels for five minutes after an upload. The versioned URL
(v = CRC32 of the bytes) changes the instant the image does, while
unchanged avatars keep enjoying the cache.
"""

import os
import zlib
from unittest.mock import patch

from pyramid.testing import DummyRequest, setUp, tearDown

from alirpunkto.views import avatar as av

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _url(jpeg):
    with patch.object(av, "get_member_avatar", return_value=jpeg):
        config = setUp()
        try:
            config.add_route("member_avatar", "/member_avatar")
            return av.avatar_url(DummyRequest(), "oid-1")
        finally:
            tearDown()


def test_the_token_follows_the_bytes():
    url_a = _url(b"AAAA-image-bytes")
    url_b = _url(b"BBBB-image-bytes")
    assert url_a != url_b
    expected = format(zlib.crc32(b"AAAA-image-bytes") & 0xffffffff, "x")
    assert f"v={expected}" in url_a


def test_missing_or_failing_storage_degrades_to_a_stable_url():
    assert "v=0" in _url(None)
    with patch.object(av, "get_member_avatar",
                      side_effect=RuntimeError("ldap down")):
        config = setUp()
        try:
            config.add_route("member_avatar", "/member_avatar")
            url = av.avatar_url(DummyRequest(), "oid-1")
        finally:
            tearDown()
    assert "v=0" in url


def test_the_templates_use_the_versioned_url():
    template = open(os.path.join(
        ROOT, "alirpunkto", "templates", "modify_member.pt"),
        encoding="utf-8").read()
    assert "avatar_url(am_oid)" in template
    assert "avatar_url(admin_view['oid'])" in template
    assert "'?oid=' + str" not in template, (
        "a hand-concatenated avatar URL bypasses the version token")


def test_the_helper_is_a_renderer_global():
    source = open(os.path.join(ROOT, "alirpunkto", "__init__.py"),
                  encoding="utf-8").read()
    assert "event['avatar_url']" in source
