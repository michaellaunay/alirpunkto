"""The daily maintenance runs inside the application (issue #269).

Issue #148 wants a daily scan of the Dynamic Groups and issue #269 wants
its result propagated to the SSO infrastructure the same day; both
treatments existed but nothing scheduled them — and no external process
can, the ZODB FileStorage being locked by the running application. The
app factory now starts one daemon thread when ``daily_maintenance.enabled``
is set: a first pass after ``initial_delay`` seconds, then one every
``interval`` seconds, each pass purging the expired quarantines and
re-synchronising the groups.
"""
from __future__ import annotations

import configparser
import os
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import alirpunkto
import alirpunkto.maintenance as mt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ------------------------------ the switch -------------------------------- #
def test_the_thread_is_not_started_when_disabled():
    with patch.object(mt.threading, 'Thread') as thread:
        assert mt.start_daily_maintenance(object(), {}) is None
        assert mt.start_daily_maintenance(
            object(), {mt.SETTING_ENABLED: 'false'}) is None
    thread.assert_not_called()


def test_the_thread_is_started_as_a_daemon_with_the_configured_cadence():
    registry = object()
    with patch.object(mt.threading, 'Thread') as thread:
        started = mt.start_daily_maintenance(registry, {
            mt.SETTING_ENABLED: 'true',
            mt.SETTING_INITIAL_DELAY: '5',
            mt.SETTING_INTERVAL: '3600'})
    kwargs = thread.call_args.kwargs
    assert kwargs['target'] is mt.maintenance_loop
    assert kwargs['args'] == (registry, 5.0, 3600.0)
    assert kwargs['daemon'] is True
    assert kwargs['name'] == mt.THREAD_NAME
    thread.return_value.start.assert_called_once()
    assert started is thread.return_value


def test_the_defaults_are_two_minutes_then_daily():
    with patch.object(mt.threading, 'Thread') as thread:
        mt.start_daily_maintenance(object(), {mt.SETTING_ENABLED: 'yes'})
    assert thread.call_args.kwargs['args'][1:] == (120, 86400)


def test_an_invalid_cadence_falls_back_or_refuses():
    with patch.object(mt.threading, 'Thread') as thread:
        mt.start_daily_maintenance(object(), {
            mt.SETTING_ENABLED: 'true', mt.SETTING_INITIAL_DELAY: 'soon',
            mt.SETTING_INTERVAL: '-1'})
    # a negative interval falls back to the default, a non-number too
    assert thread.call_args.kwargs['args'][1:] == (120, 86400)
    with patch.object(mt.threading, 'Thread') as thread:
        assert mt.start_daily_maintenance(object(), {
            mt.SETTING_ENABLED: 'true', mt.SETTING_INTERVAL: '0'}) is None
    thread.assert_not_called()


# ------------------------------- the loop --------------------------------- #
def test_the_loop_waits_the_initial_delay_then_the_interval():
    sleeps, runs = [], []
    stop = threading.Event()

    def sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 3:
            stop.set()

    mt.maintenance_loop('reg', 7, 100, sleep=sleep, stop=stop,
                        run=lambda registry: runs.append(registry))
    assert sleeps == [7, 100, 100]
    assert runs == ['reg', 'reg']


def test_a_crashing_pass_does_not_end_the_loop():
    stop = threading.Event()
    calls = []

    def sleep(_):
        if len(calls) == 2:
            stop.set()

    def run(registry):
        calls.append(registry)
        raise RuntimeError('boom')

    mt.maintenance_loop('reg', 0, 0, sleep=sleep, stop=stop, run=run)
    assert len(calls) == 2


# -------------------------------- one pass -------------------------------- #
def _env(members):
    request = SimpleNamespace()
    env = {'request': request}
    conn = MagicMock()
    conn.root.return_value = {'members': members} if members is not None else {}
    prepared = MagicMock()
    prepared.__enter__ = MagicMock(return_value=env)
    prepared.__exit__ = MagicMock(return_value=False)
    return request, prepared, conn


def test_a_pass_purges_in_its_own_transaction_then_scans_the_groups():
    members = {'m': object()}
    request, prepared, conn = _env(members)
    with patch.object(mt, 'prepare', return_value=prepared), \
         patch('pyramid_zodbconn.get_connection', return_value=conn), \
         patch('alirpunkto.utils.purge_unsubscribed_members',
               return_value=['gone-1']) as purge, \
         patch('alirpunkto.dynamic_groups.daily_group_scan',
               return_value=['moved-1']) as scan, \
         patch.object(mt.transaction, 'commit') as commit, \
         patch.object(mt.transaction, 'abort') as abort:
        report = mt.run_daily_maintenance('registry', today='T', now='N')
    assert report == {'purged': ['gone-1'], 'changed': ['moved-1']}
    purge.assert_called_once_with(request, now='N', members=members)
    scan.assert_called_once_with(request, today='T')
    commit.assert_called_once()
    abort.assert_not_called()


def test_a_failing_purge_is_aborted_and_the_scan_still_runs():
    request, prepared, conn = _env({'m': object()})
    with patch.object(mt, 'prepare', return_value=prepared), \
         patch('pyramid_zodbconn.get_connection', return_value=conn), \
         patch('alirpunkto.utils.purge_unsubscribed_members',
               side_effect=RuntimeError('ldap down')), \
         patch('alirpunkto.dynamic_groups.daily_group_scan',
               return_value=[]) as scan, \
         patch.object(mt.transaction, 'commit') as commit, \
         patch.object(mt.transaction, 'abort') as abort:
        report = mt.run_daily_maintenance('registry')
    assert report == {'purged': [], 'changed': []}
    abort.assert_called_once()
    commit.assert_not_called()
    scan.assert_called_once()


def test_an_empty_database_skips_the_purge_without_touching_the_singleton():
    request, prepared, conn = _env(None)
    with patch.object(mt, 'prepare', return_value=prepared), \
         patch('pyramid_zodbconn.get_connection', return_value=conn), \
         patch('alirpunkto.utils.purge_unsubscribed_members') as purge, \
         patch('alirpunkto.utils.get_members') as singleton, \
         patch('alirpunkto.dynamic_groups.daily_group_scan',
               return_value=[]), \
         patch.object(mt.transaction, 'commit'):
        mt.run_daily_maintenance('registry')
    purge.assert_not_called()
    singleton.assert_not_called()


def test_the_purge_accepts_a_mapping_without_rebinding_the_singleton():
    """``purge_unsubscribed_members(members=...)`` is what lets the
    background thread work on its own connection's mapping."""
    from alirpunkto import utils
    with patch.object(utils, 'get_members') as singleton:
        assert utils.purge_unsubscribed_members(
            SimpleNamespace(), members={}) == []
    singleton.assert_not_called()


def test_a_pass_runs_against_the_real_registry(app):
    """No mock around the ZODB plumbing: ``prepare`` on the app's
    registry, the thread's own connection, the real root and a real
    commit — only the directory-facing scan is stubbed."""
    with patch('alirpunkto.dynamic_groups.daily_group_scan',
               return_value=[]) as scan:
        report = mt.run_daily_maintenance(app.registry)
    assert report == {'purged': [], 'changed': []}
    scan.assert_called_once()


# ------------------------------- the wiring ------------------------------- #
def test_the_app_factory_starts_the_maintenance(app_settings):
    # An in-memory ZODB: the session-wide app holds the FileStorage lock.
    settings = dict(app_settings, **{'zodbconn.uri': 'memory://'})
    with patch.object(alirpunkto, 'create_ldap_groups_if_not_exists',
                      return_value=None), \
         patch('alirpunkto.utils.get_ldap_member_list', return_value=[]), \
         patch('alirpunkto.maintenance.start_daily_maintenance') as start:
        alirpunkto.main({}, **settings)
    start.assert_called_once()
    registry, settings = start.call_args.args
    assert settings.get(mt.SETTING_ENABLED) is not None


def _ini(name):
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(os.path.join(ROOT, name), encoding='utf-8')
    return parser['app:main']


def test_production_enables_the_maintenance_and_the_test_configs_do_not():
    assert _ini('production.ini').get(mt.SETTING_ENABLED) == 'true'
    assert _ini('test_production.ini').get(mt.SETTING_ENABLED) == 'true'
    assert _ini('testing.ini').get(mt.SETTING_ENABLED) == 'false'
    assert _ini('development.ini').get(mt.SETTING_ENABLED) == 'false'
