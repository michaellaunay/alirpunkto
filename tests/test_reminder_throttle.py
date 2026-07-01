"""Unit tests for the verifier-reminder throttle (audit finding 2.18).

``remind_pending_verifiers`` is subscribed to every request. It runs the scan at
most once per interval and under a non-blocking lock, so it neither fires on
every request nor double-sends concurrently. The interval is configurable: a
``verifier_reminder_min_interval_seconds`` production.ini setting takes
precedence over the ``VERIFIER_REMINDER_MIN_INTERVAL_SECONDS`` env/.env constant
(default 72h). The ``PYTEST_CURRENT_TEST`` short-circuit is bypassed here to
exercise the throttle.
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import alirpunkto as app
from alirpunkto.constants_and_globals import VERIFIER_REMINDER_MIN_INTERVAL_SECONDS


def _event(settings=None):
    return SimpleNamespace(
        request=SimpleNamespace(
            registry=SimpleNamespace(settings=settings if settings is not None else {})
        )
    )


def _patch_send(monkeypatch):
    sent = MagicMock()
    monkeypatch.setattr(
        "alirpunkto.views.register.send_verifier_reminder_emails", sent
    )
    return sent


def test_reminder_is_skipped_under_pytest(monkeypatch):
    sent = _patch_send(monkeypatch)

    app.remind_pending_verifiers(_event())  # PYTEST_CURRENT_TEST is truthy

    sent.assert_not_called()


def test_reminder_runs_at_most_once_per_interval(monkeypatch):
    monkeypatch.setattr(app, "PYTEST_CURRENT_TEST", False)
    monkeypatch.setattr(
        app, "_reminder_last_run",
        time.monotonic() - VERIFIER_REMINDER_MIN_INTERVAL_SECONDS - 1,
    )
    sent = _patch_send(monkeypatch)

    app.remind_pending_verifiers(_event())
    app.remind_pending_verifiers(_event())  # within the interval -> throttled

    assert sent.call_count == 1


def test_reminder_runs_again_after_the_interval(monkeypatch):
    monkeypatch.setattr(app, "PYTEST_CURRENT_TEST", False)
    monkeypatch.setattr(
        app, "_reminder_last_run",
        time.monotonic() - VERIFIER_REMINDER_MIN_INTERVAL_SECONDS - 1,
    )
    sent = _patch_send(monkeypatch)

    app.remind_pending_verifiers(_event())
    # Simulate the throttle interval having elapsed.
    app._reminder_last_run = time.monotonic() - VERIFIER_REMINDER_MIN_INTERVAL_SECONDS - 1
    app.remind_pending_verifiers(_event())

    assert sent.call_count == 2


def test_production_ini_setting_overrides_the_default_interval(monkeypatch):
    # A small interval provided via settings must be used instead of the 72h
    # default: a last run 11s ago is beyond a 10s interval, so it runs (whereas
    # the default would throttle it).
    monkeypatch.setattr(app, "PYTEST_CURRENT_TEST", False)
    monkeypatch.setattr(app, "_reminder_last_run", time.monotonic() - 11)
    sent = _patch_send(monkeypatch)

    event = _event(settings={"verifier_reminder_min_interval_seconds": 10})
    app.remind_pending_verifiers(event)

    sent.assert_called_once()
