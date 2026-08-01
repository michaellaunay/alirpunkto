"""The sender of every e-mail is never a person (issue #69).

The From used to be a personal address, then a resolution that always
overwrote the .ini value — down to the literal string 'default_sender'
used as a From when the environment was silent. The cascade is now: the
MAIL_SENDER environment variable, then a non-empty mail.default_sender
from the .ini, then the generic welcome@<domain> the ticket asks for —
always a plausible address. The single sending path reads the resolved
settings value, so the whole application follows.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import alirpunkto
from alirpunkto import resolve_mail_sender

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_the_environment_variable_wins():
    with patch.object(alirpunkto, 'MAIL_SENDER',
                      'welcome@access.cosmopolitical.coop'):
        sender = resolve_mail_sender(
            {'mail.default_sender': 'other@example.com'})
    assert sender == 'welcome@access.cosmopolitical.coop'


def test_the_ini_value_is_respected_when_the_environment_is_silent():
    """The regression that kept the ticket alive: the old code always
    overwrote the .ini value, so configuring the sender there did
    nothing."""
    with patch.object(alirpunkto, 'MAIL_SENDER', None), \
         patch.dict(os.environ, {}, clear=False):
        os.environ.pop('MAIL_SENDER', None)
        sender = resolve_mail_sender(
            {'mail.default_sender': 'welcome@example.coop'})
    assert sender == 'welcome@example.coop'


def test_the_fallback_is_a_plausible_address_never_a_placeholder():
    with patch.object(alirpunkto, 'MAIL_SENDER', None), \
         patch.object(alirpunkto, 'DOMAIN_NAME', 'example.com'):
        os.environ.pop('MAIL_SENDER', None)
        for settings in ({}, {'mail.default_sender': ''},
                         {'mail.default_sender': '   '},
                         {'mail.default_sender': 'default_sender'},
                         {'mail.default_sender': 'None'}):
            sender = resolve_mail_sender(settings)
            assert sender == 'welcome@example.com', settings
            assert sender != 'default_sender'


def test_the_wiring_goes_through_the_resolver():
    source = open(os.path.join(ROOT, 'alirpunkto', '__init__.py'),
                  encoding='utf-8').read()
    assert ("settings['mail.default_sender'] = "
            "resolve_mail_sender(settings)") in source
    assert "os.environ.get('MAIL_SENDER', 'default_sender')" not in source


def test_no_personal_address_survives_in_the_repository():
    """The ticket's grievance itself: the sender bound the platform to a
    person. No production file may carry a personal cosmopolitical or
    logikascium address as a sender."""
    import subprocess
    out = subprocess.run(
        ['grep', '-rn', '--include=*.py', '--include=*.ini',
         '--include=*.pt', 'publicpolicies.cosmopolitical',
         os.path.join(ROOT, 'alirpunkto'),
         os.path.join(ROOT, 'development.ini'),
         os.path.join(ROOT, 'production.ini')],
        capture_output=True, text=True)
    assert out.stdout.strip() == ''
