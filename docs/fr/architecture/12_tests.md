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

## Campagne 2026-08-01, suite : 894 tests

Deux leçons de plus. **Un validateur construit à la définition de classe
se fige à l'import** : la borne d'âge du champ date de naissance
(`get_majority_date()`) datait du démarrage du process — après quelques
semaines, le formulaire refusait des candidats devenus majeurs
entre-temps. Le remède est le **`colander.deferred`**, résolu à chaque
`bind` donc à chaque requête, verrouillé par un test qui déplace la
majorité de soixante jours et vérifie que le bind la suit. Et côté
harnais : un clone de vérification a besoin de son `var/` — sans lui, la
ZODB échoue en `zc.lockfile` et six tests fonctionnels passent en erreur
fantôme.

## Campagne de l'audit externe (2026-08-01) : 931 tests

Le journal en direct de pytest devient **opt-in** (`log_cli = false`) :
la suite exerce volontairement les branches d'échec — LDAP injoignable,
valeurs d'énumération inconnues, envois refusés — dont les `log.error`
sont le comportement vérifié ; un passage vert criait des dizaines de
lignes `[ERROR]`. Les tests en échec conservent leurs journaux capturés
dans leur propre rapport, et le direct revient à la demande
(`pytest -o log_cli=true`). Côté chaîne de construction : les
dépendances sont bornées dans `pyproject.toml` (versions mesurées sur
l'environnement testé), épinglées dans `requirements.lock` (77 paquets,
provenance commentée), et la CI installe ce verrou — sa clé de cache,
jadis dérivée de `setup.py`, suit `pyproject.toml` et le verrou. Six
tests d'empaquetage verrouillent l'ensemble, `setup.py` compris dans
son absence.

## Portes de qualité (2026-08-02) : 1022 tests

La CI ne se contente plus d'exécuter la suite : un second workflow
(`quality.yml`) rend **Ruff bloquant** (famille Pyflakes ; `F841` en
exception documentée, prochain cran du cliquet), **Bandit bloquant**
dès la sévérité moyenne (les deux SHA-1 du format `{SSHA}` portent
leur `# nosec` motivé — c'est le format que consomme slapd), et
**pip-audit sur le verrou** (une seule exception, documentée dans le
workflow même : `PYSEC-2026-3447`, un setuptools transitif retenu par
la chaîne deform). Les mesures ont précédé les portes : 137 constats
Ruff ramenés à zéro, dont deux vrais défauts — un `global DOMAINE`
manquant qui cassait le repli d'un outil, et un `from requests import
request` qui masquait le paramètre des vues (et fabriquait au passage
cinq faux positifs Bandit). La couverture, mesurée à ~70 %, reçoit un
plancher `--cov-fail-under=68` — un cliquet, pas une cible. Toutes les
actions GitHub sont épinglées par SHA de commit (le tag lisible en
commentaire), plus aucune installation hors verrou ne subsiste dans
les workflows (`--allow-unsafe` épingle pip/setuptools/wheel dans le
verrou), et mypy entre en observateur (`continue-on-error`, 124
erreurs à l'adoption). `tests/test_quality_gates.py` verrouille le
câblage lui-même : gates invoquées, plancher armé, chaque `uses:` en
SHA de 40, zéro installation hors verrou, plancher `cryptography`
conservé. Leçon de harnais : ne jamais « restaurer » une démonstration
rouge par `git checkout --` — il ramène HEAD et détruit les correctifs
non commis ; seule la copie de côté est sûre.

Les trains 0071→0078 ont porté la suite de 957 à **1022 tests**, en
verrouillant chaque acquis par une **démonstration rouge** sur l'état
antérieur : démarrage Docker et overrides serveur
(`test_docker_startup.py`) ; chaîne d'approvisionnement — trois verrous
hachés, extension identique, voies CI (`test_supply_chain.py`) ;
finition d'image jusqu'à la **parité réelle de la wheel** — le test
reconstruit la wheel applicative et exige les 449 fichiers suivis
(`test_image_finishing.py`) ; transport LDIF sur l'entrée standard
avec champs requis obligatoires (`test_ldif_transport.py`) ; contrat
des **appelants** du générateur — les trois appelants sourcent
l'émetteur commun, parité émetteur↔générateur par `ast`, YAML compose
sans clé dupliquée, porte `config --quiet` avant tout build
(`test_ldif_callers.py`) ;
scellement du jeton SSO et budget cookie mesuré sur jeton
incompressible ; validation des réponses Keycloak ; et cohérence des
groupes jusqu'aux **vetos d'écriture injectés** et aux latchs à moitié
levés non ressuscités (`test_group_coherence.py`). La couverture
atteint 72,10 % au-dessus du plancher de 68.
