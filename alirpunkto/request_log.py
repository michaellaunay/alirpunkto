"""Request trace and last-resort exception log of the application.

Production diagnosis of 2026-10-30: a navigation answered "Internal
Server Error" and ``var/log/alirpunkto.log`` stayed empty although the
``alirpunkto`` logger runs at DEBUG. The logging configuration of
``production.ini`` splits the streams: the application logger writes
to its file with ``propagate = 0``, while an exception escaping a view
is reported by Waitress on ITS OWN logger ("Exception while serving
…"), which only the root handler sees — stderr, hence the systemd
journal — never the application file. Nothing in the application
logged the request either, so the file had no trace of the navigation
at all.

This tween is the outermost of the chain (right under ``INGRESS``,
above ``pyramid_tm`` and the exception views): every request passes
through it, and every exception that escapes the whole stack crosses
it on the way out, BEFORE Waitress turns it into a bare 500. It gives
the application log the complete story of a navigation:

- ``request METHOD path?names from client`` at DEBUG on entry — the
  query carries only its parameter NAMES (an SSO ``code``, an
  encrypted ``oid`` link, a ``state`` never reach the log; transversal
  audit of 2026-10-24, A12);
- ``response … -> status route=name [user=pseudonym] in N ms`` at
  DEBUG, at WARNING for a 5xx the stack built itself. The pseudonym is
  read only when the request already opened its session: the tween
  never opens one (a signed-cookie session is re-issued on access);
- ``unhandled ExcType on … after N ms`` at ERROR WITH the traceback,
  then the exception is re-raised unchanged for the server.
"""
from __future__ import annotations

import json
import logging
import time

from pyramid.tweens import INGRESS

from alirpunkto.constants_and_globals import log

#: Dotted name under which the tween is registered (``ptweens`` shows it).
TWEEN_NAME = 'alirpunkto.request_log.request_log_tween_factory'


def describe_request(request) -> str:
    """``METHOD /path?name1,name2 from client`` — parameter names only,
    never their values, never a header, never a body."""
    client = getattr(request, 'client_addr', None) or '-'
    try:
        names = ','.join(sorted(set(request.GET.keys())))
    except Exception:  # pragma: no cover - a hostile query string
        names = '?'
    path = request.path + (f"?{names}" if names else '')
    return f"{request.method} {path} from {client}"


def session_user(request) -> str | None:
    """The pseudonym of the session's user when the request ALREADY
    opened its session, else None — the tween must not open one."""
    session = request.__dict__.get('session')
    if session is None:
        return None
    try:
        raw = session.get('user')
    except Exception:  # pragma: no cover - a session look-alike
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        return data.get('name') or data.get('oid') or None
    except (ValueError, AttributeError):
        return None


def describe_response(request, response) -> str:
    route = getattr(getattr(request, 'matched_route', None), 'name', None)
    parts = [f"-> {response.status}"]
    if route:
        parts.append(f"route={route}")
    user = session_user(request)
    if user:
        parts.append(f"user={user}")
    return ' '.join(parts)


def request_log_tween_factory(handler, registry):
    def request_log_tween(request):
        started = time.monotonic()
        summary = describe_request(request)
        log.debug("request %s", summary)
        try:
            response = handler(request)
        except Exception as exc:
            elapsed = int((time.monotonic() - started) * 1000)
            log.exception("unhandled %s on %s after %d ms: %s",
                          type(exc).__name__, summary, elapsed, exc)
            raise
        elapsed = int((time.monotonic() - started) * 1000)
        level = (logging.WARNING if response.status_code >= 500
                 else logging.DEBUG)
        log.log(level, "response %s %s in %d ms",
                summary, describe_response(request, response), elapsed)
        return response
    return request_log_tween


def includeme(config):
    """``config.include('alirpunkto.request_log')``: outermost tween."""
    config.add_tween(TWEEN_NAME, under=INGRESS)
