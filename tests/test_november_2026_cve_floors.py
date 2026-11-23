"""November 2026 advisories — pyasn1, soupsieve, msgpack (train 0127).

The quality CI went red on 30 October 2026 on ``pip-audit`` alone, for
advisories published after the October trains (0116, 0118) had computed
the locks:

* pyasn1 0.6.4 — CVE-2026-119194/119195/119196/119197: four decoder
  paths (schemaless containers with many long tag IDs, fragmented
  OCTET and BIT STRINGs, a REAL with a large mantissa) spend CPU time
  quadratic in the size of the encoded input. Fixed in 0.6.5. This is
  the one runtime package of the three: ``ldap3`` decodes every answer
  of the directory through it.
* soupsieve 2.9.2 — CVE-2026-126190/126191/126192/126193: polynomial or
  exponential time, or unbounded recursion, on hostile selectors or
  deeply nested documents. The last fix landed in 4.0.0. Test lock
  only (beautifulsoup4, under WebTest).
* msgpack 1.2.2 — CVE-2026-114613: the C extension leaks a decoded map
  value each time a key is rejected. Fixed in 1.2.3. Quality lock only
  (cachecontrol, under pip-audit).

The floors keep the next ``pip-compile`` from sliding back into the
vulnerable ranges; the round trip checks that ``ldap3`` — which still
imports pyasn1's deprecated encoder tables — works on the raised pin.
"""
from __future__ import annotations

import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLOORS = [
    ("requirements.lock", "pyasn1", (0, 6, 5)),
    ("requirements-test.lock", "pyasn1", (0, 6, 5)),
    ("requirements-quality.lock", "pyasn1", (0, 6, 5)),
    ("requirements-test.lock", "soupsieve", (4, 0, 0)),
    ("requirements-quality.lock", "msgpack", (1, 2, 3)),
]


def _pinned(lock, package):
    text = open(os.path.join(ROOT, lock), encoding="utf-8").read()
    match = re.search(rf"^{package}==([\d.]+)", text, re.M)
    assert match, (lock, package)
    return tuple(int(part) for part in match.group(1).split("."))


@pytest.mark.parametrize("lock, package, floor", FLOORS,
                         ids=[f"{lock}:{package}" for lock, package, _ in FLOORS])
def test_the_lock_carries_the_advisory_floor(lock, package, floor):
    assert _pinned(lock, package) >= floor, (lock, package)


def test_ldap3_still_speaks_ber_on_the_raised_pyasn1():
    """A bind request encoded by ldap3 decodes back to itself."""
    from ldap3.operation.bind import bind_operation
    from ldap3.protocol.rfc4511 import LDAPMessage, MessageID, ProtocolOp
    from ldap3.utils.asn1 import decoder, encode

    message = LDAPMessage()
    message['messageID'] = MessageID(7)
    message['protocolOp'] = ProtocolOp().setComponentByName(
        'bindRequest',
        bind_operation(3, 'SIMPLE', 'cn=reader,dc=example,dc=com', 'x'))
    decoded, rest = decoder.decode(encode(message), asn1Spec=LDAPMessage())

    assert not rest
    assert int(decoded['messageID']) == 7
    assert str(decoded['protocolOp']['bindRequest']['name']) == \
        'cn=reader,dc=example,dc=com'
