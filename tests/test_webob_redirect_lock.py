"""WebOb 1.8.11 — the Location-header open redirect stays closed (0113).

PYSEC-2026-3943 / CVE-2026-54770 / GHSA-6hx8-3wjj-gr8g: up to WebOb
1.8.10, ``Response._make_location_absolute()`` ran its scheme and ``//``
guards on the raw value but resolved it with ``urllib.parse.urljoin()``,
which on Python 3.10+ first strips leading C0 control characters and
spaces — so ``" //evil.example/"`` slipped past both guards and came
back as ``http://evil.example/``. The ``_HTTPMove`` exceptions
(``HTTPFound`` and friends) never went through that method at all and
let a protocol-relative location out as-is.

Two layers are locked here:

1. the library itself, with the advisory's own reproducers — a red
   test on 1.8.10, green on 1.8.11 — so a lock regeneration can never
   silently reintroduce the vulnerable range;
2. ``safe_local_redirect`` (train 0063), which already refused these
   payloads before the library was fixed: ``strip()`` removes the
   leading space and a bare C0 byte is not a rooted path. Defence in
   depth is only worth something if both layers are tested.
"""
from __future__ import annotations

import os
import re
from types import SimpleNamespace

import pytest
from webob import Response, exc
from webob.request import Request

from alirpunkto.utils import safe_local_redirect

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST_REQ = SimpleNamespace(host="site.test")

SMUGGLED = [
    " //www.example.com/test",          # leading space, protocol-relative
    " https://www.example.com/test",    # leading space, absolute
    "\x00//www.example.com/test",       # NUL
    "\x1f//www.example.com/test",       # last C0 control
    "\t//www.example.com/test",         # the 1.8.10 strip, still refused
]


# ------------------------------ the library ------------------------------- #
@pytest.mark.parametrize("location", SMUGGLED)
def test_a_smuggled_response_location_stays_on_host(location):
    """Advisory PoC 1: ``Response.location`` must not resolve off-host."""
    res = Response()
    res.status = "301"
    res.location = location
    req = Request.blank("/")            # host is "localhost"
    final = req.get_response(res).location
    assert final.startswith("http://localhost/"), final
    assert "www.example.com" not in final.split("//", 1)[1].split("/", 1)[0]


def test_a_protocol_relative_httpfound_is_neutralised():
    """Advisory PoC 2: the exception path also normalises ``//``."""
    environ = {
        "wsgi.url_scheme": "http", "SERVER_NAME": "localhost",
        "SERVER_PORT": "80", "REQUEST_METHOD": "HEAD", "PATH_INFO": "/",
    }
    move = exc.HTTPFound(location="//www.example.com/test")
    move(environ, lambda *a, **k: None)
    assert move.location == "http://localhost/%2fwww.example.com/test"


# ------------------------------ the app guard ----------------------------- #
@pytest.mark.parametrize("url", SMUGGLED)
def test_safe_local_redirect_refuses_the_smuggled_forms(url):
    assert safe_local_redirect(url, HOST_REQ) is None


# ------------------------------ the locks --------------------------------- #
@pytest.mark.parametrize("lock", [
    "requirements.lock", "requirements-test.lock", "requirements-quality.lock",
])
def test_webob_carries_the_cve_floor(lock):
    text = open(os.path.join(ROOT, lock), encoding="utf-8").read()
    match = re.search(r"^webob==([\d.]+)", text, re.M)
    assert match, lock
    assert tuple(map(int, match.group(1).split("."))) >= (1, 8, 11), (lock, match.group(1))
