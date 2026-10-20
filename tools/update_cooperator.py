#!/usr/bin/env python3
"""
Script to update LDAP contributor data via the AlirPunkto portal.

Author: Michaël Launay
Date: 2025-06-29
Email: michaellaunay@logikascium.com
Version: 0.2

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

Raises:
    FileNotFoundError: If the specified .env file is not found.
    ValueError: If login credentials are invalid or input data is incorrect.
    RuntimeError: If the portal refuses or does not confirm the update.

Returns:
    None
"""

from typing import Final
import argparse
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import requests

# Constantes

DOMAINE = "https://alirpunkto.cosmopolitical.coop"
LOGIN_PATH= "login"
LOGIN_URL = f"{DOMAINE}/{LOGIN_PATH}"
MODIFY_PATH = "modify_member"
MODIFY_URL = f"{DOMAINE}/{MODIFY_PATH}"
CONTRIBUTION_PATH = "update_contribution"
CONTRIBUTION_URL = f"{DOMAINE}/{CONTRIBUTION_PATH}"

#: The hidden field every page of a logged-in session carries.
CSRF_MARKER: Final[str] = 'name="csrf_token" value="'

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
    """
    session.post(LOGIN_URL, data={
        "username": username,
        "password": password,
        "form.submitted": "True"
    })
    # A logged-in session renders the member directory with its CSRF
    # field; an anonymous one is sent back to the home page without it.
    page = session.get(MODIFY_URL)
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

def modify_member(session: requests.Session, oid: str, shares: str | None,
                  validity_date: str | None, csrf_token: str) -> dict:
    """
    Sends the modifications (shares / membership validity date) of one
    member to the portal and returns the portal's JSON answer.
    """
    # If no modifications are requested, stop here
    if not shares and not validity_date:
        print("No modifications requested.")
        return {}

    post_data = {
        "oid": oid,
        "csrf_token": csrf_token,
    }

    if shares:
        if not shares.strip().isdigit():
            raise ValueError("The number of shares must be a non-negative integer.")
        post_data["number_shares_owned"] = shares.strip()

    if validity_date:
        # Check the date format before sending it
        try:
            datetime.strptime(validity_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("The validity date must be in the format YYYY-MM-DD.")
        post_data["date_end_validity_yearly_contribution"] = validity_date

    update_res = session.post(CONTRIBUTION_URL, data=post_data)
    try:
        answer = update_res.json()
    except ValueError:
        raise RuntimeError(
            f"The portal did not answer JSON (HTTP {update_res.status_code}); "
            "is the base URL right?")

    if update_res.status_code == 200 and answer.get("status") == "success":
        print("✅ Data successfully updated.")
        print(f"   shares: {answer.get('number_shares_owned')}, "
              f"validity: {answer.get('date_end_validity_yearly_contribution')}, "
              f"groups: {', '.join(answer.get('groups', [])) or '-'}")
    else:
        raise RuntimeError(
            f"⚠️ The update was refused (HTTP {update_res.status_code}): "
            f"{answer.get('error', 'unknown error')} "
            f"{answer.get('fields', '')}".strip())
    return answer

# Entry point
def main() -> None:
    args = parse_args()

    load_env_file(args.env)
    global DOMAINE          # ruff F823: the fallback read the global,
    DOMAINE = args.base_url or os.getenv("base_url") or DOMAINE  # noqa: E501
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
