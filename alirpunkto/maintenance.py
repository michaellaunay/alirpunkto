"""The daily maintenance of the directory (issue #269).

Issue #148 asks AlirPunkto to scan the directory **every day** — an
expired yearly contribution moves a Cooperator out of ``cooperatorsGroup``,
a quarantine that ends erases a resigned member — and issue #269 adds the
second step: the members whose Dynamic Group changed must reach the SSO
infrastructure the same day. Both treatments existed as callable
functions (``dynamic_groups.daily_group_scan``,
``utils.purge_unsubscribed_members``) but nothing ever called them: the
documentation delegated the scheduling to an external ``cron``, which
cannot work with the shipped stack — the ZODB ``FileStorage`` is held
exclusively by the running application, so a second process opening it
fails (``tools/run_upgrades.py`` says as much).

The maintenance therefore runs **inside the application**, in one daemon
thread started by the app factory when ``daily_maintenance.enabled`` is
true (``production.ini``): a first pass ``daily_maintenance.initial_delay``
seconds after start-up, then one every ``daily_maintenance.interval``
seconds (a day by default). Every pass is idempotent, so a restart that
repeats one is harmless, and a failing pass only logs — the next one
retries. Waitress is a single multi-threaded process, hence one thread.
"""
from __future__ import annotations

import threading
import time

import transaction
from pyramid.scripting import prepare
from pyramid.settings import asbool

from alirpunkto.constants_and_globals import log

SETTING_ENABLED = 'daily_maintenance.enabled'
SETTING_INITIAL_DELAY = 'daily_maintenance.initial_delay'
SETTING_INTERVAL = 'daily_maintenance.interval'

DEFAULT_INITIAL_DELAY = 120          # seconds after start-up
DEFAULT_INTERVAL = 24 * 60 * 60      # once a day

THREAD_NAME = 'alirpunkto-daily-maintenance'


def run_daily_maintenance(registry, *, today=None, now=None) -> dict:
    """One maintenance pass against ``registry``'s databases.

    1. purge the resigned members whose Quarantine expired (ZODB + LDAP,
       committed here — no request transaction wraps a background
       thread);
    2. re-synchronise the Dynamic Groups of every managed member
       (calendar-driven transitions of #148), which propagates the moves
       to Keycloak when any member changed group (#269).

    Returns ``{'purged': [...], 'changed': [...]}``; never raises.
    """
    from alirpunkto.dynamic_groups import daily_group_scan
    from alirpunkto.utils import purge_unsubscribed_members
    report = {'purged': [], 'changed': []}
    with prepare(registry=registry) as env:
        request = env['request']
        try:
            members = _members_of(request)
            if members is not None:
                report['purged'] = purge_unsubscribed_members(
                    request, now=now, members=members)
            transaction.commit()
        except Exception as exc:
            transaction.abort()
            log.error(f"daily maintenance: purge failed: "
                      f"{exc.__class__.__name__}: {exc}")
        try:
            report['changed'] = daily_group_scan(request, today=today)
        except Exception as exc:
            log.error(f"daily maintenance: group scan failed: "
                      f"{exc.__class__.__name__}: {exc}")
    log.info(f"daily maintenance: {len(report['purged'])} member(s) "
             f"purged, {len(report['changed'])} member(s) moved between "
             "groups")
    return report


def _members_of(request):
    """The members mapping of the thread's own ZODB connection, read
    without rebinding the ``Members`` singleton (not thread safe: the
    request threads own it). None when the database has no mapping yet
    — then there is nothing to purge."""
    from pyramid_zodbconn import get_connection
    # ``conn.root()`` (called) is the persistent root mapping itself;
    # the same two operations Members.get_instance uses on it.
    root = get_connection(request).root()
    return root['members'] if 'members' in root else None


def maintenance_loop(registry, initial_delay, interval, *,
                     sleep=time.sleep, stop=None, run=None):
    """Run passes forever: the first after ``initial_delay`` seconds, the
    next ones ``interval`` seconds apart. ``stop`` (a threading.Event)
    ends the loop; ``sleep`` and ``run`` are injectable for tests."""
    run = run or run_daily_maintenance
    delay = initial_delay
    while True:
        sleep(delay)
        if stop is not None and stop.is_set():
            return
        try:
            run(registry)
        except Exception as exc:
            # The pass itself never raises; this is the last safety net
            # so that the thread outlives any surprise.
            log.error(f"daily maintenance: pass crashed: "
                      f"{exc.__class__.__name__}: {exc}")
        delay = interval


def start_daily_maintenance(registry, settings) -> threading.Thread | None:
    """Start the maintenance thread when ``daily_maintenance.enabled`` is
    set; returns the thread, or None when disabled."""
    if not asbool(settings.get(SETTING_ENABLED, False)):
        log.info("daily maintenance: disabled "
                 f"({SETTING_ENABLED} is not true)")
        return None
    initial_delay = _non_negative(settings, SETTING_INITIAL_DELAY,
                                  DEFAULT_INITIAL_DELAY)
    interval = _non_negative(settings, SETTING_INTERVAL, DEFAULT_INTERVAL)
    if interval <= 0:
        log.error(f"daily maintenance: {SETTING_INTERVAL} must be a "
                  "positive number of seconds; thread not started")
        return None
    thread = threading.Thread(
        target=maintenance_loop,
        args=(registry, initial_delay, interval),
        name=THREAD_NAME,
        daemon=True,
    )
    thread.start()
    log.info(f"daily maintenance: thread started (first pass in "
             f"{initial_delay} s, then every {interval} s)")
    return thread


def _non_negative(settings, key, default):
    raw = settings.get(key, default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        log.error(f"daily maintenance: {key}={raw!r} is not a number; "
                  f"using {default}")
        return default
    if value < 0:
        log.error(f"daily maintenance: {key}={raw!r} is negative; "
                  f"using {default}")
        return default
    return value
