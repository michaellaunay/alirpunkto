# Tests

> Statut : documentation courante.
> Emplacement : `tests/` (plus de 580 tests au 2026-07-25).

## Lancement

```bash
export SECRET_KEY=... LDAP_PASSWORD=... ADMIN_PASSWORD=... MAIL_PASSWORD=...
mkdir -p var
pytest tests
```

Les quatre secrets doivent exister dans l'environnement (voir
`alirpunkto/secret_manager.py`) et `var/` doit exister pour la ZODB de test.

## LDAP simulé par défaut

Hors pile Docker, `ldap_factory` bascule automatiquement sur un serveur
simulé (`MOCK_SYNC`, schéma `OFFLINE_SLAPD_2_4`) dès que
`PYTEST_CURRENT_TEST` est défini et que `TEST_WITH_DOCKER_LDAP` ne l'est
pas : la suite s'exécute sans annuaire. Les tests d'intégration réels
passent par la pile locale (`docker/test-docker-compose.yaml`,
`docker/README_TEST_LOCAL.md`).

## Familles de tests

- **Vues et modèles** : unités classiques (`test_views.py`,
  `test_home_sso.py`, …).
- **Internationalisation** : rendu des courriels d'inscription dans toutes
  les locales et pour tous les types de membres ; rendu des courriels de
  résultat (7 langues × 2 gabarits × 2 modes `textual`), parité `.po`/`.mo`
  via le vrai *localizer*, langue préférée du destinataire et négociateur
  de locale.
- **Sécurité, par constat d'audit** : chaque constat corrigé a son fichier —
  `test_security_1_3_password_hashing.py` (hachage `{SSHA}`, purge ZODB),
  `test_ldap_schema_tolerance.py`, `test_session_cookie_budget.py`.
- **Migration et provisionnement** : `test_migrate_ldap_legacy_remote.py`,
  `test_ldap_provision.py`.
- **Non-régression d'incidents** : `test_zodb_repopulation_from_ldap.py`
  (reconstruction de la ZODB depuis LDAP).

## Intégration continue

Le *workflow* GitHub Actions (`.github/workflows/tests.yml`) exécute la
suite sur Python 3.11 et 3.12 à chaque *push* et *pull request* : cache pip
indexé sur `setup.py` (`cache-dependency-path`), création de `var/`, export
des secrets de test, rapport `junitxml` publié en artefact. Un correctif
n'est considéré livrable que la matrice au vert.

## Convention du projet

Tout correctif issu d'un audit ou d'un incident de terrain est **verrouillé
par des tests dédiés**, datés dans leur docstring : la suite raconte
l'histoire des constats et empêche leur retour. Un correctif sans test
n'est pas considéré comme clos.
