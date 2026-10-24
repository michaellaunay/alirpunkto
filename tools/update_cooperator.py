#!/usr/bin/env python3
"""
Script to update LDAP contributor data via the AlirPunkto portal.

Author: Michaël Launay
Date: 2026-10-24
Email: michaellaunay@logikascium.com
Version: 0.4

This script allows updating contributor data such as the number of shares
or membership validity date by interacting with the AlirPunkto platform.
It is the "Python script of the online commercial site" of issue #75: the
shop calls it as soon as a Cooperator pays, and the portal moves the
member between the Dynamic Groups and tells the SSO infrastructure at
once (issues #267 and #269).

Since issue #149 another member's profile is a read-only card for
everyone, administrators included, so the script no longer drives the
profile form: it posts to the dedicated ``/update_contribution`` endpoint
(administrator session and CSRF token required) and reads its JSON answer.

Version 0.4 (external audit of 2026-10-24) — what the wire really wants:

* the portal's CSRF guard is global: the login POST itself needs the
  ``csrf_token`` of the login page and, over HTTPS, an ``Origin`` (or
  ``Referer``) header naming the portal — a bare POST is a 400;
* ``0`` is a legitimate number of shares, and a call that asks for no
  change at all is an error, never a silent exit 0 (A1);
* the answer is checked, not trusted: the OID and every fact sent must
  come back confirmed (A3), and a ``partial`` status — facts recorded,
  groups or SSO lagging — is reported as a failure to retry (A2);
* every HTTP call carries a timeout (A4), tokens are never printed.

Exit code 0 means, and only means: the portal confirmed that the facts
are in the directory with the values requested, that the member's
Dynamic Groups converged and that the Keycloak synchronisation ran
without reported failure. It does not prove that every client
application has already refreshed its own authorisations. Anything
else exits 1 with the portal's reason.

Raises:
    FileNotFoundError: If the specified .env file is not found.
    ValueError: If login credentials are invalid or input data is incorrect.
    RuntimeError: If the portal refuses, does not confirm or only partly
        applies the update.
"""

from __future__ import annotations

from typing import Final
import argparse
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from dotenv import load_dotenv
import requests

# Constants

DOMAINE = "https://alirpunkto.cosmopolitical.coop"
LOGIN_PATH = "login"
LOGIN_URL = f"{DOMAINE}/{LOGIN_PATH}"
MODIFY_PATH = "modify_member"
MODIFY_URL = f"{DOMAINE}/{MODIFY_PATH}"
CONTRIBUTION_PATH = "update_contribution"
CONTRIBUTION_URL = f"{DOMAINE}/{CONTRIBUTION_PATH}"

SHARES_FIELD: Final[str] = "number_shares_owned"
VALIDITY_FIELD: Final[str] = "date_end_validity_yearly_contribution"
DATE_FORMAT: Final[str] = "%Y-%m-%d"

#: The hidden field every page of a session carries.
CSRF_MARKER: Final[str] = 'name="csrf_token" value="'

#: (connect, read) seconds — a stuck portal must not stall the shop (A4).
TIMEOUT: Final[tuple[int, int]] = (10, 30)

#: A business ceiling on one member's shares: anything above is a caller
#: bug (an overflow, a misplaced amount), refused before it reaches the
#: directory (second audit pass, P4).
MAX_SHARES: Final[int] = 1_000_000

#: A validity date outside this window is a typo, not a contribution
#: (third audit pass: ``0000-01-01`` must not travel).
MIN_YEAR: Final[int] = 1900
MAX_YEAR: Final[int] = 2199


# Functions
def load_env_file(env_path: Path) -> None:
    """
    Loads environment variables from the specified .env file.
    """
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        raise FileNotFoundError(f".env file not found at location: {env_path}")


def parse_args() -> argparse.Namespace:
    """
    Parses command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Login and member modification for Alirpunkto.")
    parser.add_argument("--env", "-e", type=Path, default=Path(".env"),
                        help="Path to the .env file (default: ./env)")
    parser.add_argument("--login", "-l", type=str, help="Login (overrides .env)")
    parser.add_argument("--password", "-p", type=str, help="Password (overrides .env)")
    parser.add_argument("--cookie", "-c", type=Path,
                        help="Path to the file to store session cookies")
    parser.add_argument("--oid", "-o", type=str, required=True,
                        help="OID of the member to modify")
    parser.add_argument("--number-shares", type=str, help="Number of shares to specify")
    parser.add_argument("--validity-date", type=str, help="End date of membership validity (YYYY-MM-DD)")
    # Transversal audit of 2026-10-24 (A15): no default here — a non-empty
    # argparse default used to shadow the .env value entirely.
    parser.add_argument("--base_url", type=str, default=None,
                        help="Portal origin, https://host (overrides .env)")
    parser.add_argument("--allow-http", action="store_true",
                        help="Accept http:// for localhost only (local tests)")
    return parser.parse_args()


#: Hosts for which --allow-http is honoured.
LOCAL_HOSTS: Final[tuple[str, ...]] = ("localhost", "127.0.0.1", "::1", "[::1]")


def portal_origin(base_url: str, allow_http: bool = False) -> str:
    """``scheme://host[:port]`` of the portal — the value of the Origin
    header the CSRF guard compares with the request host. A base URL
    with a path or no host is refused rather than silently mangled, and
    plain http only for a local host with --allow-http: an administrator
    password travels on this connection (A15)."""
    parts = urlsplit(base_url)
    if parts.scheme not in ("http", "https") or not parts.netloc \
            or parts.path not in ("", "/") or parts.query or parts.fragment:
        raise ValueError(
            f"base_url must be the portal's origin (scheme://host), got {base_url!r}")
    if parts.scheme != "https" and not (
            allow_http and parts.hostname in LOCAL_HOSTS):
        raise ValueError(
            "base_url must use https (the administrator password travels on it); "
            "--allow-http is honoured for localhost only.")
    return f"{parts.scheme}://{parts.netloc}"


def same_origin(location: str | None, origin: str) -> bool:
    """True when a redirect Location stays on the portal: relative, or
    same scheme, host and port."""
    if not location:
        return False
    target = urlsplit(location)
    if not target.scheme and not target.netloc:
        return True
    expected = urlsplit(origin)
    defaults = {"http": 80, "https": 443}
    return (target.scheme == expected.scheme
            and (target.hostname or "").lower() == (expected.hostname or "").lower()
            and (target.port or defaults.get(target.scheme))
            == (expected.port or defaults.get(expected.scheme)))


def csrf_headers() -> dict[str, str]:
    """Pyramid's CSRF guard checks, over HTTPS, that the Origin (or the
    Referer) of every unsafe request names the portal itself."""
    origin = portal_origin(DOMAINE)
    return {"Origin": origin, "Referer": f"{origin}/"}


def extract_csrf_token(html: str) -> str:
    """The CSRF token of the session, read from a rendered page."""
    try:
        return html.split(CSRF_MARKER)[1].split('"')[0]
    except IndexError:
        raise RuntimeError("Unable to extract the CSRF token.")


def login(session: requests.Session, username: str, password: str) -> str:
    """
    Logs into the Alirpunkto portal, initializes the session and returns
    the CSRF token of that session.

    1. GET the login page: it opens the session and carries its token;
    2. POST the credentials WITH that token and the Origin header — the
       global CSRF guard refuses a bare POST with a 400;
    3. GET the member directory: a logged-in session renders it with its
       CSRF field, an anonymous one is sent back to the home page without
       it — that is the login check, and the token the update needs.
    """
    login_page = session.get(LOGIN_URL, timeout=TIMEOUT)
    if CSRF_MARKER not in login_page.text:
        raise RuntimeError(
            f"The login page carries no CSRF token (HTTP {login_page.status_code}); "
            "is the base URL right?")
    login_token = extract_csrf_token(login_page.text)

    # A15: the credentials POST is never replayed through a redirect —
    # the portal's own 302 is recognised, not followed.
    answer = session.post(LOGIN_URL, data={
        "username": username,
        "password": password,
        "csrf_token": login_token,
        "form.submitted": "True"
    }, headers=csrf_headers(), timeout=TIMEOUT, allow_redirects=False)
    if answer.status_code >= 500:
        raise RuntimeError(
            f"The portal failed on the login request (HTTP {answer.status_code}).")
    if answer.status_code >= 400:
        # A 400 here is the CSRF guard (token or Origin), never the
        # credentials — say so instead of blaming the password (A7).
        raise RuntimeError(
            f"The portal refused the login request (HTTP {answer.status_code}): "
            "CSRF token or Origin not accepted, or the portal is down.")
    if answer.status_code >= 300:
        location = answer.headers.get("Location") if answer.headers else None
        if not same_origin(location, portal_origin(DOMAINE, allow_http=True)):
            raise RuntimeError(
                f"Unexpected redirect away from the portal: {location!r}")
    else:
        # 200: the login form came back — the credentials were refused.
        raise ValueError("Login failed: invalid credentials.")

    page = session.get(MODIFY_URL, timeout=TIMEOUT)
    if CSRF_MARKER not in page.text:
        raise ValueError("Login failed: invalid credentials.")
    return extract_csrf_token(page.text)


def save_cookies(session: requests.Session, path: Path) -> None:
    """
    Saves session cookies to a text file.
    """
    # A15: the file holds an administrator session — private to this
    # account, created or truncated with 0600.
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as f:
        for cookie in session.cookies:
            f.write(f"{cookie.name}={cookie.value}\n")
    os.chmod(path, 0o600)


def check_requested_changes(shares: str | None, validity_date: str | None) -> dict:
    """The facts to send, validated — or ValueError. ``"0"`` shares is a
    value, not an absence; no fact at all is a caller bug (A1)."""
    post_data: dict[str, str] = {}
    if shares is not None and shares.strip() != "":
        if not shares.strip().isdigit():
            raise ValueError("The number of shares must be a non-negative integer.")
        value = int(shares.strip())
        if value > MAX_SHARES:
            raise ValueError(
                f"The number of shares must not exceed {MAX_SHARES} (second audit pass, P4).")
        post_data[SHARES_FIELD] = str(value)
    if validity_date is not None and validity_date.strip() != "":
        try:
            day = datetime.strptime(validity_date.strip(), DATE_FORMAT)
        except ValueError:
            raise ValueError("The validity date must be in the format YYYY-MM-DD.")
        if not MIN_YEAR <= day.year <= MAX_YEAR:
            raise ValueError(
                f"The validity date must fall between {MIN_YEAR} and {MAX_YEAR}.")
        post_data[VALIDITY_FIELD] = validity_date.strip()
    if not post_data:
        raise ValueError(
            "At least one financial fact (--number-shares or --validity-date) is required.")
    return post_data


def check_answer(answer: dict, oid: str, sent: dict) -> None:
    """The portal's success answer must describe THIS member with THE
    values sent (A3); a ``partial`` status means the facts are recorded
    but the rights are not yet restored — a failure to retry (A2)."""
    if answer.get("oid") != oid:
        raise RuntimeError(
            f"The portal answered for member {answer.get('oid')!r}, not {oid!r}.")
    for field, value in sent.items():
        if str(answer.get(field)) != value:
            raise RuntimeError(
                f"The portal did not confirm {field}: sent {value!r}, "
                f"recorded {answer.get(field)!r}.")
    if answer.get("status") == "partial":
        raise RuntimeError(
            "⚠️ Facts recorded but rights NOT fully restored: "
            f"groups_sync={answer.get('groups_sync')}, "
            f"keycloak_sync={answer.get('keycloak_sync')}, "
            f"groups={answer.get('groups')} — run the same command again.")
    if answer.get("status") != "success":
        raise RuntimeError(f"Unexpected portal status {answer.get('status')!r}.")
    # Second audit pass (P3): "success" alone is not enough — each of the
    # three steps must say so, and the groups must be a real list.
    if answer.get("financial_update") not in ("success", "unchanged"):
        raise RuntimeError("The portal did not confirm the financial update.")
    for step in ("groups_sync", "keycloak_sync"):
        if answer.get(step) != "success":
            raise RuntimeError(
                f"The portal did not confirm {step} (got {answer.get(step)!r}).")
    if not isinstance(answer.get("groups"), list):
        raise RuntimeError("The portal did not return the member's groups.")


def modify_member(session: requests.Session, oid: str, shares: str | None,
                  validity_date: str | None, csrf_token: str) -> dict:
    """
    Sends the modifications (shares / membership validity date) of one
    member to the portal, checks the portal's JSON answer and returns it.
    """
    post_data = {"oid": oid, "csrf_token": csrf_token}
    post_data.update(check_requested_changes(shares, validity_date))
    sent = {k: v for k, v in post_data.items() if k in (SHARES_FIELD, VALIDITY_FIELD)}

    update_res = session.post(CONTRIBUTION_URL, data=post_data,
                              headers=csrf_headers(), timeout=TIMEOUT,
                              allow_redirects=False)
    if 300 <= update_res.status_code < 400:
        raise RuntimeError(
            f"The portal redirected the update request (HTTP {update_res.status_code}); "
            "the session is not an administrator's or the base URL is wrong.")
    try:
        answer = update_res.json()
    except ValueError:
        raise RuntimeError(
            f"The portal did not answer JSON (HTTP {update_res.status_code}); "
            "is the base URL right?")
    if not isinstance(answer, dict):
        raise RuntimeError(
            f"The portal answered something that is not an object (HTTP {update_res.status_code}).")

    if update_res.status_code != 200:
        raise RuntimeError(
            f"⚠️ The update was refused (HTTP {update_res.status_code}): "
            f"{answer.get('error', 'unknown error')} "
            f"{answer.get('fields', '')}".strip())
    check_answer(answer, oid, sent)
    print("✅ Data successfully updated.")
    print(f"   shares: {answer.get(SHARES_FIELD)}, "
          f"validity: {answer.get(VALIDITY_FIELD)}, "
          f"groups: {', '.join(answer.get('groups') or []) or '-'}")
    return answer


# Entry point
def main() -> None:
    args = parse_args()

    # Refuse a no-op before opening any session (A1).
    check_requested_changes(args.number_shares, args.validity_date)

    if args.login and args.password and not args.env.exists():
        pass            # credentials on the command line: the file is optional
    else:
        load_env_file(args.env)
    global DOMAINE          # ruff F823: the fallback read the global,
    # Priority (A15): command line, then .env, then the built-in default.
    DOMAINE = portal_origin(args.base_url or os.getenv("base_url") or DOMAINE,
                            allow_http=args.allow_http)
    global LOGIN_URL
    LOGIN_URL = f"{DOMAINE}/{LOGIN_PATH}"
    global MODIFY_URL
    MODIFY_URL = f"{DOMAINE}/{MODIFY_PATH}"
    global CONTRIBUTION_URL
    CONTRIBUTION_URL = f"{DOMAINE}/{CONTRIBUTION_PATH}"

    login_val = args.login or os.getenv("login")
    password_val = args.password or os.getenv("password")

    if not login_val or not password_val:
        raise ValueError("Login and password must be defined in the .env file or provided as parameters.")

    with requests.Session() as session:
        csrf_token = login(session, login_val, password_val)

        if args.cookie:
            save_cookies(session, args.cookie)

        modify_member(
            session=session,
            oid=args.oid,
            shares=args.number_shares,
            validity_date=args.validity_date,
            csrf_token=csrf_token,
        )

if __name__ == "__main__":
    main()
