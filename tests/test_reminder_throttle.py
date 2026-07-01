"""Unit tests for the verifier-reminder throttle (audit finding 2.18).

``remind_pending_verifiers`` is subscribed to every request. It now runs the
scan at most once per interval and under a non-blocking lock, so it neither
fires on every request nor double-sends concurrently. (The ``PYTEST_CURRENT_TEST``
short-circuit is bypassed here to exercise the throttle.)
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import alirpunkto as app


def _event():
    return SimpleNamespace(request=object())


def test_reminder_is_skipped_under_pytest(monkeypatch):
    sent = MagicMock()
    monkeypatch.setattr(
        "alirpunkto.views.register.send_verifier_reminder_emails", sent
    )

    app.remind_pending_verifiers(_event())  # PYTEST_CURRENT_TEST is truthy

    sent.assert_not_called()


def test_reminder_runs_at_most_once_per_interval(monkeypatch):
    monkeypatch.setattr(app, "PYTEST_CURRENT_TEST", False)
    monkeypatch.setattr(
        app, "_reminder_last_run",
        time.monotonic() - app._REMINDER_MIN_INTERVAL_SECONDS - 1,
    )
    sent = MagicMock()
    monkeypatch.setattr(
        "alirpunkto.views.register.send_verifier_reminder_emails", sent
    )

    app.remind_pending_verifiers(_event())
    app.remind_pending_verifiers(_event())  # within the interval → throttled

    assert sent.call_count == 1


def test_reminder_runs_again_after_the_interval(monkeypatch):
    monkeypatch.setattr(app, "PYTEST_CURRENT_TEST", False)
    monkeypatch.setattr(
        app, "_reminder_last_run",
        time.monotonic() - app._REMINDER_MIN_INTERVAL_SECONDS - 1,
    )
    sent = MagicMock()
    monkeypatch.setattr(
        "alirpunkto.views.register.send_verifier_reminder_emails", sent
    )

    app.remind_pending_verifiers(_event())
    # Simulate the throttle interval having elapsed.
    app._reminder_last_run = time.monotonic() - app._REMINDER_MIN_INTERVAL_SECONDS - 1
    app.remind_pending_verifiers(_event())

    assert sent.call_count == 2
