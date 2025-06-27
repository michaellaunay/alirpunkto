#!/usr/bin/env python3

from typing import Final
import argparse
import os
from pathlib import Path
from dotenv import load_dotenv
import requests

# --- Constantes ---

LOGIN_URL: Final[str] = "https://alirpunkto.cosmopolitical.coop/login"
MODIFY_URL: Final[str] = "https://alirpunkto.cosmopolitical.coop/modify_member"

# Messages de succès dans plusieurs langues
SUCCESS_MESSAGES: Final[list[str]] = [
    "Member data updated",               # anglais
    "Données du membre mises à jour",   # français
]

# --- Fonctions ---

def load_env_file(env_path: Path) -> None:
    """
    Charge les variables d’environnement depuis le fichier .env donné.
    """
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        raise FileNotFoundError(f".env introuvable à l’emplacement : {env_path}")

def parse_args() -> argparse.Namespace:
    """
    Analyse les arguments de ligne de commande.
    """
    parser = argparse.ArgumentParser(description="Connexion et modification de membre Alirpunkto.")
    parser.add_argument("--env", "-e", type=Path, default=Path(".env"),
                        help="Chemin du fichier .env (défaut : ./env)")
    parser.add_argument("--login", "-l", type=str, help="Login (prioritaire sur .env)")
    parser.add_argument("--password", "-p", type=str, help="Mot de passe (prioritaire sur .env)")
    parser.add_argument("--cookie", "-c", type=Path,
                        help="Chemin du fichier pour stocker les cookies de session")
    parser.add_argument("--oid", "-o", type=str, required=True,
                        help="OID du membre à modifier")
    parser.add_argument("--number-shares", type=str, help="Nombre de parts sociales à renseigner")
    parser.add_argument("--validity-date", type=str, help="Date de fin de validité de la cotisation (YYYY-MM-DD)")
    return parser.parse_args()

def login(session: requests.Session, username: str, password: str) -> None:
    """
    Se connecte au portail Alirpunkto et initialise la session.
    """
    res = session.post(LOGIN_URL, data={
        "username": username,
        "password": password,
        "form.submitted": "true"
    })
    if "Connexion" in res.text or "Connection" in res.text:
        raise ValueError("Échec de la connexion : identifiants invalides.")

def save_cookies(session: requests.Session, path: Path) -> None:
    """
    Sauvegarde les cookies de session dans un fichier texte.
    """
    with open(path, "w") as f:
        for cookie in session.cookies:
            f.write(f"{cookie.name}={cookie.value}\n")

def modify_member(session: requests.Session, oid: str, shares: str | None, validity_date: str | None) -> None:
    """
    Sélectionne un membre puis envoie les modifications (parts / date cotisation).
    """
    # Étape 1 : sélection du membre
    select_res = session.post(MODIFY_URL, data={"accessed_member_oid": oid})
    if "Veuillez sélectionner" in select_res.text or "Please select" in select_res.text:
        raise RuntimeError("Erreur de sélection du membre (mauvais OID ?)")

    # Si aucune modif demandée, on s’arrête ici
    if not shares and not validity_date:
        print("Aucune modification demandée.")
        return

    # Étape 2 : récupération du token CSRF
    try:
        csrf_token = select_res.text.split('name="csrf_token" value="')[1].split('"')[0]
    except IndexError:
        raise RuntimeError("Impossible d’extraire le token CSRF.")

    # Étape 3 : préparation des données du POST
    post_data = {
        "csrf_token": csrf_token,
        "modify": "modify"
    }

    if shares:
        post_data["number_shares_owned"] = shares

    if validity_date:
        post_data["__start__"] = "date_end_validity_yearly_contribution:mapping"
        post_data["date"] = validity_date
        post_data["__end__"] = "date_end_validity_yearly_contribution:mapping"

    # Étape 4 : envoi des modifications
    update_res = session.post(MODIFY_URL, data=post_data)

    # Vérification de la réponse : multi-langue
    if any(success_msg in update_res.text for success_msg in SUCCESS_MESSAGES):
        print("✅ Données mises à jour avec succès.")
    else:
        print("⚠️ La mise à jour n’a pas été confirmée. Vérifie manuellement.")

# --- Point d’entrée ---

def main() -> None:
    args = parse_args()

    load_env_file(args.env)

    login_val = args.login or os.getenv("login")
    password_val = args.password or os.getenv("password")

    if not login_val or not password_val:
        raise ValueError("Le login et le mot de passe doivent être définis dans .env ou en paramètre.")

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