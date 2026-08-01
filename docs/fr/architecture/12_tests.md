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

## Campagne 2026-07-30

La suite est passée d'environ 580 à **plus de 800** tests. Leçons de
harnais durables, encodées dans les tests eux-mêmes : l'annuaire **mock
`ldap3`** (`client_strategy=MOCK_SYNC`) se lie **anonymement** (pas
d'utilisateur fictif) et rend les dates en chaînes — les adaptateurs les
parsent ; le rendu de gabarits sous `pytest` exige le **threadlocal**
poussé (`pyramid.threadlocal.manager.push({'request': …, 'registry': …})`) ;
un test qui rend un formulaire `deform` épingle
`deform.form.Form.default_renderer` pour rester hermétique au renderer
global qu'un autre test installe ; le widget de date soumet une structure
**peppercorn** (`__start__`/`date`/`__end__`), comme un navigateur ; et la
table de vérité des groupes dynamiques est verrouillée **cas par cas**
contre le ticket #148 par des tests paramétrés.

## Campagne 2026-08-01

La suite atteint **867 tests**. La leçon qui restera : `@view_config`
est un *veneer* — il retourne la fonction inchangée et marque pour
`config.scan`. Une fonction glissée **entre** le décorateur et la `def`
devient silencieusement LA vue de la route : les tests qui appellent la
vue directement restent verts, la production sert un 500. Le correctif
du groupe 4 recolle le décorateur et pose un **verrou structurel**
(`test_the_view_config_decorates_the_view_itself`). Autres acquis : la
matrice de l'issue #55 est verrouillée **cas par cas** par une table
paramétrée calquée sur le ticket (dix-neuf régimes), et les rendus de
gabarits s'assertent sur les **msgstr des catalogues**, jamais sur les
textes de repli inline.
