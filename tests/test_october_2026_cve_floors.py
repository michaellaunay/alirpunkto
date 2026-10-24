"""October 2026 advisories — pyjwt, urllib3, certifi (0116), filelock (0118).

The quality CI went red on 20 October 2026 on ``pip-audit`` alone, for
advisories published after the September train (0113) had computed the
locks:

* PyJWT 2.14.0 — PYSEC-2026-4141 / CVE-2026-101918: a payload that is
  valid JSON nested thousands of levels deep makes ``json.loads`` raise
  ``RecursionError`` inside ``jwt.decode``, which only caught
  ``ValueError`` — an undocumented exception type escaping the
  documented ``PyJWTError`` family. PYSEC-2026-4183 / CVE-2026-102275:
  ``OKPAlgorithm.from_jwk`` did not check that the private scalar ``d``
  matches the public ``x``. Both fixed in 2.15.0.
* urllib3 2.7.0 — PYSEC-2026-4175/4176/4177 (CVE-2026-97687/97688/
  97689): proxy TLS settings bleeding into the target connection, an
  infinite loop on trailing bytes after a Deflate stream, and an
  unbounded chunk-size field in the streaming decoder. Fixed in 2.8.0.
* certifi 2026.7.22 — PYSEC-2026-4320: the bundle still trusted
  ``emSign ECC Root CA - G3``, whose eMudhra intermediates had their
  private keys compromised. Removed in 2026.10.18; the unaffected
  emSign roots were restored in 2026.10.19.

AlirPunkto's own ``jwt.decode`` call (``views/sso_login.py``) verifies
the signature, so the nested-payload path is only reachable with a
token minted by the Keycloak back channel — a low exposure, but the
library reproducer is cheap and the lock floor is what keeps the next
``pip-compile`` from sliding back into the vulnerable range.
"""
from __future__ import annotations

import base64
import os
import re

import certifi
import jwt
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCKS = (
    "requirements.lock", "requirements-test.lock", "requirements-quality.lock",
)
FLOORS = {
    "pyjwt": (2, 15, 0),
    "urllib3": (2, 8, 0),
    "certifi": (2026, 10, 19),
}


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


# ------------------------------ the libraries ----------------------------- #
def test_a_deeply_nested_payload_raises_a_documented_jwt_error():
    """PYSEC-2026-4141 reproducer: the caller's ``except PyJWTError``
    must see the failure — never a bare ``RecursionError``."""
    depth = 10_000
    payload = ("[" * depth + "]" * depth).encode("ascii")
    token = ".".join((_b64(b'{"alg":"none","typ":"JWT"}'), _b64(payload), ""))
    with pytest.raises(jwt.exceptions.PyJWTError):
        jwt.decode(token, options={"verify_signature": False})


def test_the_compromised_emsign_root_is_out_of_the_bundle():
    """PYSEC-2026-4320: ``requests`` and ``python-keycloak`` verify the
    Keycloak server through this bundle."""
    with open(certifi.where(), encoding="utf-8") as handle:
        bundle = handle.read()
    assert "emSign ECC Root CA - G3" not in bundle


# ------------------------------ the locks --------------------------------- #
def _pinned(lock, package):
    text = open(os.path.join(ROOT, lock), encoding="utf-8").read()
    match = re.search(rf"^{package}==([\d.]+)", text, re.M)
    assert match, (lock, package)
    return tuple(int(part) for part in match.group(1).split("."))


@pytest.mark.parametrize("lock", LOCKS)
@pytest.mark.parametrize("package", sorted(FLOORS))
def test_the_lock_carries_the_advisory_floor(lock, package):
    pinned = _pinned(lock, package)
    assert pinned >= FLOORS[package], (lock, package, pinned)


def test_the_quality_lock_carries_the_filelock_floor():
    """Train 0118: filelock 3.32.6 — CVE-2026-112907/112913/112940
    (SQLite-backed and soft locks abused by another local account),
    fixed in 4.2.1. Only the quality lane carries it (via
    cachecontrol, under pip-audit)."""
    assert _pinned("requirements-quality.lock", "filelock") >= (4, 2, 1)


def test_the_setuptools_ignores_are_both_dated_in_the_workflow():
    """The two accepted setuptools advisories share one blocker (deform
    3.0.1 / pyramid 2.1 pin setuptools below the fix) and one class
    (installation paths, never runtime); each carries its review date
    so the next reader knows when to look again."""
    workflow = open(os.path.join(ROOT, ".github", "workflows", "quality.yml"),
                    encoding="utf-8").read()
    for advisory, reviewed in (("PYSEC-2026-3447", "2026-09-12"),
                               ("GHSA-xmj3-9gf7-h52w", "2026-10-24")):
        assert f"--ignore-vuln {advisory}" in workflow, advisory
        assert f"Reviewed {reviewed}" in workflow, advisory
