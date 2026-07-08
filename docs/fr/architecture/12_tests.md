# Tests

> Statut : documentation courante.
> Emplacement : `tests/` (plus de 420 tests au 2026-07-08).

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
  les locales et pour tous les types de membres.
- **Sécurité, par constat d'audit** : chaque constat corrigé a son fichier —
  `test_security_1_3_password_hashing.py` (hachage `{SSHA}`, purge ZODB),
  `test_ldap_schema_tolerance.py`, `test_session_cookie_budget.py`.
- **Migration et provisionnement** : `test_migrate_ldap_legacy_remote.py`,
  `test_ldap_provision.py`.
- **Non-régression d'incidents** : `test_zodb_repopulation_from_ldap.py`
  (reconstruction de la ZODB depuis LDAP).

## Convention du projet

Tout correctif issu d'un audit ou d'un incident de terrain est **verrouillé
par des tests dédiés**, datés dans leur docstring : la suite raconte
l'histoire des constats et empêche leur retour. Un correctif sans test
n'est pas considéré comme clos.
