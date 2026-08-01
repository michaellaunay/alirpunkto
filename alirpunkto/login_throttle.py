"""Login attempt throttling (external audit, 2026-08-01).

The login view used to reach the LDAP directory on every attempt with no
limit — open to brute force, credential stuffing and directory
saturation. Two sliding windows now guard it, checked *before* any LDAP
work: per client IP (a spray from one address) and, stricter, per
username (a targeted attack from many addresses). A successful login
clears both counters; a throttled attempt is answered uniformly and
logged without the password.

The state is in-process memory under a lock, which matches the deployed
architecture — one Waitress process serving threads — with no new
dependency and no I/O on the hot path. Running several replicas would
give each its own counters (the limit multiplies by the replica count):
good enough against brute force, but a shared store belongs to the
server-side-session work if the deployment ever scales out. For the IP
window to see real client addresses behind Apache, Waitress must trust
the proxy (``trusted_proxy`` in ``production.ini``); otherwise every
request carries the proxy's address and the IP window throttles everyone
together.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


#: A single address: at most 10 attempts over 5 minutes.
IP_MAX_ATTEMPTS = 10
IP_WINDOW_SECONDS = 300

#: A single username, from any address: at most 5 attempts over 15 minutes.
USERNAME_MAX_ATTEMPTS = 5
USERNAME_WINDOW_SECONDS = 900

_lock = threading.Lock()
_attempts: dict = defaultdict(deque)


def _now() -> float:
    return time.monotonic()


def _purge(key, window: float, now: float) -> deque:
    timestamps = _attempts[key]
    while timestamps and now - timestamps[0] > window:
        timestamps.popleft()
    if not timestamps:
        _attempts.pop(key, None)
    return timestamps


def is_throttled(client_ip: str, username: str) -> bool:
    """True when either sliding window is full. Call before any LDAP work."""
    now = _now()
    with _lock:
        ip_hits = len(_purge(('ip', client_ip), IP_WINDOW_SECONDS, now))
        name_hits = len(_purge(('name', username.strip().lower()),
                               USERNAME_WINDOW_SECONDS, now))
    return (ip_hits >= IP_MAX_ATTEMPTS
            or name_hits >= USERNAME_MAX_ATTEMPTS)


def record_failure(client_ip: str, username: str) -> None:
    now = _now()
    with _lock:
        _attempts[('ip', client_ip)].append(now)
        _attempts[('name', username.strip().lower())].append(now)


def record_success(client_ip: str, username: str) -> None:
    """A legitimate login clears the *username* counter only.

    Revised audit, 2026-08-01: clearing the IP counter too let an
    attacker holding one valid account reset the address window at will
    — probe several usernames, log into their own account, repeat. The
    legitimate user regains access through their username counter; the
    address keeps its history until the window expires on its own.
    """
    with _lock:
        _attempts.pop(('name', username.strip().lower()), None)


def _reset_for_tests() -> None:
    with _lock:
        _attempts.clear()
