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

Exit code 0 means, and only means: the facts are in the directory with
the values requested, the member's Dynamic Groups are converged and the
change reached Keycloak. Anything else exits 1 with the portal's reason.

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
    parser.add_argument("--base_url", type=str, default=DOMAINE,)
    return parser.parse_args()


def portal_origin(base_url: str) -> str:
    """``scheme://host[:port]`` of the portal — the value of the Origin
    header the CSRF guard compares with the request host. A base URL
    with a path or no host is refused rather than silently mangled."""
    parts = urlsplit(base_url)
    if parts.scheme not in ("http", "https") or not parts.netloc \
            or parts.path not in ("", "/") or parts.query or parts.fragment:
        raise ValueError(
            f"base_url must be the portal's origin (scheme://host), got {base_url!r}")
    return f"{parts.scheme}://{parts.netloc}"


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

    answer = session.post(LOGIN_URL, data={
        "username": username,
        "password": password,
        "csrf_token": login_token,
        "form.submitted": "True"
    }, headers=csrf_headers(), timeout=TIMEOUT)
    if answer.status_code >= 400:
        # A 400 here is the CSRF guard (token or Origin), never the
        # credentials — say so instead of blaming the password (A7).
        raise RuntimeError(
            f"The portal refused the login request (HTTP {answer.status_code}): "
            "CSRF token or Origin not accepted, or the portal is down.")

    page = session.get(MODIFY_URL, timeout=TIMEOUT)
    if CSRF_MARKER not in page.text:
        raise ValueError("Login failed: invalid credentials.")
    return extract_csrf_token(page.text)


def save_cookies(session: requests.Session, path: Path) -> None:
    """
    Saves session cookies to a text file.
    """
    with open(path, "w") as f:
        for cookie in session.cookies:
            f.write(f"{cookie.name}={cookie.value}\n")


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
            datetime.strptime(validity_date.strip(), DATE_FORMAT)
        except ValueError:
            raise ValueError("The validity date must be in the format YYYY-MM-DD.")
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
                              headers=csrf_headers(), timeout=TIMEOUT)
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
    DOMAINE = portal_origin(args.base_url or os.getenv("base_url") or DOMAINE)  # noqa: E501
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
