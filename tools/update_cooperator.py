#!/usr/bin/env python3
"""
Script to update LDAP contributor data via the AlirPunkto portal.

Author: Michaël Launay
Date: 2025-06-29
Email: michaellaunay@logikascium.com
Version: 0.1

This script allows updating contributor data such as the number of shares 
or membership validity date by interacting with the AlirPunkto platform.

Raises:
    FileNotFoundError: If the specified .env file is not found.
    ValueError: If login credentials are invalid or input data is incorrect.
    RuntimeError: If member selection or data modification fails.

Returns:
    None
"""

from typing import Final
import argparse
import os
from pathlib import Path
from dotenv import load_dotenv
import requests

# Constantes

DOMAINE = "https://alirpunkto.cosmopolitical.coop"
LOGIN_PATH= "login"
LOGIN_URL = f"{DOMAINE}/{LOGIN_PATH}"
MODIFY_PATH = "modify_member"
MODIFY_URL = f"{DOMAINE}/{MODIFY_PATH}"

# Success messages in multiple languages
SUCCESS_MESSAGES: Final[list[str]] = [
    "Member data updated",               # anglais
    "Données du membre mises à jour",   # français
]

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

def login(session: requests.Session, username: str, password: str) -> None:
    """
    Logs into the Alirpunkto portal and initializes the session.
    """
    result = session.post(LOGIN_URL, data={
        "username": username,
        "password": password,
        "form.submitted": "True"
    })

    if not all(keyword in result.text for keyword in [username, "profile", "modify_member"]):
        raise ValueError("Login failed: invalid credentials.")

def save_cookies(session: requests.Session, path: Path) -> None:
    """
    Saves session cookies to a text file.
    """
    with open(path, "w") as f:
        for cookie in session.cookies:
            f.write(f"{cookie.name}={cookie.value}\n")

def modify_member(session: requests.Session, oid: str, shares: str | None, validity_date: str | None) -> None:
    """
    Selects a member and sends modifications (shares / membership validity date).
    """
    # Step 1: Select the member
    select_res = session.post(MODIFY_URL, data={"accessed_member_oid": oid,"submit": "Submit"})
    if oid not in select_res.text:
        raise RuntimeError("Member selection error (wrong OID?)")

    # If no modifications are requested, stop here
    if not shares and not validity_date:
        print("No modifications requested.")
        return

    # Step 2: Retrieve the CSRF token
    try:
        csrf_token = select_res.text.split('name="csrf_token" value="')[1].split('"')[0]
    except IndexError:
        raise RuntimeError("Unable to extract the CSRF token.")
    
    # Step 3: Modify member data
    post_data = {
        "accessed_member_oid": oid,
        "modify": "modify",
        "__formid__": "deform",
        "charset": "UTF-8",

    }

    if shares:
        post_data["number_shares_owned"] = shares

    if validity_date:
        # Vérification du format de la date
        try:
            from datetime import datetime
            datetime.strptime(validity_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("The validity date must be in the format YYYY-MM-DD.")
        post_data["__start__"] = "date_end_validity_yearly_contribution:mapping"
        post_data["date"] = validity_date
        post_data["__end__"] = "date_end_validity_yearly_contribution:mapping"

    # Step 4: Send the modifications
    update_res = session.post(MODIFY_URL, data=post_data)

    # Response verification: multi-language
    if any(success_msg in update_res.text for success_msg in SUCCESS_MESSAGES):
        print("✅ Data successfully updated.")
    else:
        print("⚠️ The update was not confirmed. Please check manually.")

# Entry point
def main() -> None:
    args = parse_args()

    load_env_file(args.env)
    DOMAINE = args.base_url or os.getenv("base_url") or DOMAINE
    global LOGIN_URL
    LOGIN_URL = f"{DOMAINE}/{LOGIN_PATH}"
    global MODIFY_URL
    MODIFY_URL = f"{DOMAINE}/{MODIFY_PATH}"

    login_val = args.login or os.getenv("login")
    password_val = args.password or os.getenv("password")

    if not login_val or not password_val:
        raise ValueError("Login and password must be defined in the .env file or provided as parameters.")

    with requests.Session() as session:
        login(session, login_val, password_val)

        if args.cookie:
            save_cookies(session, args.cookie)

        modify_member(
            session=session,
            oid=args.oid,
            shares=args.number_shares,
            validity_date=args.validity_date
        )

if __name__ == "__main__":
    main()