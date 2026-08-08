"""Registration journeys: ordinary member, then cooperator.

Both journeys live the real anti-spam flow: submit the e-mail and
membership choice, receive the four word-written math challenges by
e-mail, solve them like a human would, then enter the personal data.
The ordinary member is approved immediately (register.py routes
ORDINARY straight to APPROVED) and the journey closes with a real
login; the cooperator's application lands in PENDING, awaiting the
verifiers — the voting act is the next scenario of this series.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from framework import Scenario, fetch_email, solve_all_challenges  # noqa: E402

SUBMIT = 'button[type="submit"], input[type="submit"]'


def _submit(page):
    """Click the screen's single submit — the register template uses
    <input type=submit>, the deform identity form renders
    <button id=deformsubmit type=submit> (run 84789315715)."""
    page.click(SUBMIT)
    page.wait_for_load_state("load")


BASE_URL = os.environ.get("E2E_BASE_URL", "https://alirpunkto.localhost:8443")
LANG = os.environ.get("E2E_LANG", "en")


def _begin(page, scenario, email, member_type, type_fr, type_en):
    page.goto(f"{BASE_URL}/register", wait_until="load")
    scenario.step(page, "register_form",
                  "La page d'inscription : votre adresse e-mail et le "
                  f"type d'adhésion ({type_fr}).",
                  "The registration page: your e-mail address and the "
                  f"membership type ({type_en}).")
    page.fill('input[name="email"]', email)
    page.select_option('select[name="choice"]', member_type)
    scenario.step(page, "register_filled",
                  "Formulaire rempli — la candidature va être créée.",
                  "Form filled — the application is about to be created.")
    _submit(page)
    if page.locator('input[name="result_A"]').count() != 1:
        # The page did NOT reach the challenge state (e.g. the
        # e-mail could not be sent) — fail loudly with the evidence
        # instead of captioning an error screen as a success.
        scenario.step(page, "draft_submit_failed",
                      "ÉCHEC : l'écran du défi ne s'est pas affiché.",
                      "FAILURE: the challenge screen did not appear.")
        raise AssertionError("challenge form not shown after the draft submit")
    scenario.step(page, "challenge_sent",
                  "Un e-mail contenant quatre défis mathématiques écrits "
                  "en toutes lettres vous a été envoyé.",
                  "An e-mail with four math challenges written out in "
                  "words has been sent to you.")


def _solve_challenges(page, scenario, email):
    body = fetch_email(email)
    solutions = solve_all_challenges(body, LANG)
    for label, value in solutions.items():
        page.fill(f'input[name="result_{label}"]', str(value))
    scenario.step(page, "challenge_answered",
                  "Les quatre réponses calculées depuis l'e-mail reçu — "
                  "c'est la preuve d'humanité.",
                  "The four answers computed from the received e-mail — "
                  "this is the humanity proof.")
    _submit(page)


def run_ordinary(browser):
    email = os.environ.get("E2E_ORDINARY_EMAIL",
                           "dora.test@alirpunkto.localhost")
    scenario = Scenario("register_ordinary",
                        "Créer un compte de membre ordinaire",
                        "Create an ordinary member account")
    page = browser.new_context(ignore_https_errors=True,
                               viewport={"width": 1280, "height": 800},
                               locale=LANG).new_page()
    _begin(page, scenario, email, "ORDINARY", "membre ordinaire",
           "ordinary member")
    _solve_challenges(page, scenario, email)
    scenario.step(page, "identity_form",
                  "Votre humanité est confirmée : choisissez votre "
                  "pseudonyme et votre mot de passe.",
                  "Your humanity is confirmed: choose your pseudonym "
                  "and your password.")
    page.fill('input[name="pseudonym"]', "dora.test")
    page.fill('input[name="password"]', "DoraTest123!")
    page.fill('input[name="password_confirm"]', "DoraTest123!")
    _submit(page)
    if page.locator('input[name="password"]').count():
        # The identity form is still on screen: the submission was
        # refused (this is how the lang1 LDAP bug surfaced) — fail
        # loudly with the evidence.
        scenario.step(page, "identity_submit_failed",
                      "ÉCHEC : la création du compte a été refusée.",
                      "FAILURE: the account creation was refused.")
        raise AssertionError("identity submission refused")
    scenario.step(page, "approved",
                  "Le compte de membre ordinaire est créé et approuvé "
                  "immédiatement.",
                  "The ordinary member account is created and approved "
                  "immediately.")
    page.goto(f"{BASE_URL}/login", wait_until="load")
    page.fill('input[name="username"]', "dora.test")
    page.fill('input[name="password"]', "DoraTest123!")
    _submit(page)
    scenario.step(page, "first_login",
                  "Première connexion du nouveau membre ordinaire.",
                  "First login of the new ordinary member.")
    scenario.close()
    return "dora.test" in page.content()


def run_cooperator(browser):
    email = os.environ.get("E2E_COOPERATOR_EMAIL",
                           "carl.test@alirpunkto.localhost")
    scenario = Scenario("register_cooperator",
                        "Devenir Coopérateur ou Coopératrice",
                        "Become a Cooperator")
    page = browser.new_context(ignore_https_errors=True,
                               viewport={"width": 1280, "height": 800},
                               locale=LANG).new_page()
    _begin(page, scenario, email, "COOPERATOR", "Coopérateur",
           "Cooperator")
    _solve_challenges(page, scenario, email)
    scenario.step(page, "identity_form",
                  "Le Coopérateur fournit son identité (nom, prénom, date "
                  "de naissance) : elle sera vérifiée par des membres "
                  "tirés au sort.",
                  "The Cooperator provides their identity (name, "
                  "surname, birth date): it will be checked by randomly "
                  "drawn members.")
    page.fill('input[name="fullname"]', "Carl")
    page.fill('input[name="fullsurname"]', "Cooperator")
    # The deform date widget's field is named "date" (wrapped in
    # __start__/__end__ mapping markers); nationality is NOT on this
    # screen — it belongs to later profile steps.
    page.fill('input[name="date"]', "1990-01-15")
    page.fill('input[name="pseudonym"]', "carl.test")
    page.fill('input[name="password"]', "CarlTest123!")
    page.fill('input[name="password_confirm"]', "CarlTest123!")
    scenario.step(page, "identity_filled",
                  "Identité complète saisie — prête pour la vérification.",
                  "Full identity entered — ready for verification.")
    _submit(page)
    scenario.step(page, "pending_verification",
                  "La candidature est soumise : des vérificateurs tirés "
                  "au sort vont confirmer l'identité (suite au scénario "
                  "du vote).",
                  "The application is submitted: randomly drawn "
                  "verifiers will confirm the identity (continued in "
                  "the voting scenario).")
    scenario.close()
    return "carl" in page.content().lower() or "pending" in page.url
