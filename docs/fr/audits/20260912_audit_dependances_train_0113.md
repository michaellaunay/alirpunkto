# Audit des dépendances et train 0113

**Date** : 2026-09-12 · **Auditeur** : Claude (assistant de développement) · **Référence** : master `00bd677` (train 0112) · **Contre-expertise** : ChatGPT, versions 2 et 3 du dossier de pilotage (Python 3.14 qualifié à part, puis retiré du chantier) · **Décision** : Python 3.12 reste l'interpréteur cible ; la qualification 3.14 est un lot distinct, reporté.

## Chaîne des notes

Cet audit ne note pas le projet : il porte sur les quatre verrous hachés et sur le passage de la CI qualité, rouge depuis le 1ᵉʳ septembre. Il prolonge la série (12ᵉ passage interne du 20/08 : 8,8) sans la modifier.

## 1. Méthode

Lecture des quatre verrous (`requirements.lock`, `-test`, `-quality`, `-e2e`), comparaison de chaque épingle avec la dernière version stable non retirée sur PyPI, `pip-audit --no-deps` sur chaque verrou, `pip-compile --upgrade` sous Python 3.12.3, puis exécution complète : suite de tests, ruff CI-exact, bandit, pip-audit, mypy, construction de la wheel, et un aller-retour ZODB entre l'ancienne et la nouvelle pile Zope.

**Décompte** : 106 paquets distincts sur les quatre verrous (la première version de cet audit disait 105 ; la contre-expertise avait raison, `pip` n'est présent que dans le verrou qualité et avait été perdu au dédoublonnage). 74 à jour, 30 en retard, 2 vulnérabilités connues.

## 2. Vulnérabilités

### 2.1 WebOb 1.8.10 — PYSEC-2026-3943 / CVE-2026-54770 / GHSA-6hx8-3wjj-gr8g — P0, corrigé (commit A)

Jusqu'à 1.8.10, `Response._make_location_absolute()` vérifiait le schéma et le `//` sur la valeur brute mais résolvait avec `urllib.parse.urljoin()`, qui sur Python ≥ 3.10 retire d'abord les caractères de contrôle C0 et les espaces de tête : `" //evil.example/"` passait les deux gardes et sortait de l'hôte. Les exceptions `HTTPFound` et sœurs contournaient entièrement la garde. Le job `pip-audit (blocking)` de `quality.yml` n'ignorant que PYSEC-2026-3447, la CI qualité était rouge (contre-expertise : échec constaté au journal du 1ᵉʳ septembre).

Correctif : `webob==1.8.11` seul, dans les trois verrous, sans autre mouvement (`pip-compile --upgrade-package webob`). `tests/test_webob_redirect_lock.py` verrouille les deux couches : les reproducteurs de l'avis contre la bibliothèque (5 rouges sur 1.8.10, verts sur 1.8.11) et `safe_local_redirect` du train 0063, qui refusait déjà ces charges (`strip()` retire l'espace ; un octet C0 nu n'est pas un chemin enraciné), plus un plancher `>= 1.8.11` par verrou.

### 2.2 setuptools 80.10.2 — PYSEC-2026-3447 / CVE-2026-59890 — inchangé, ignore daté

Toujours bloqué : `deform 3.0.1` déclare `setuptools<81`, `pyramid 2.1` déclare `<82`, et **tous deux importent `pkg_resources` à l'exécution** (`pyramid/asset.py`, `deform/template.py`). Correctif en 83.0.0. La CVE concerne la construction de sdist sur macOS (normalisation Unicode de `MANIFEST.in`), hors du chemin d'exécution et hors de l'image. L'ignore est conservé et porte désormais sa date de revue et son déclencheur (deform 3.1 ou pyramid 2.2). L'import direct de `pkg_resources` par AlirPunkto est migré (commit C) — hygiène, pas levée du blocage.

## 3. Inventaire des retards et décisions

| Paquet | Avant | Après | Décision |
|---|---|---|---|
| webob | 1.8.10 | 1.8.11 | **CVE**, commit A |
| cryptography | 50.0.0 | 50.0.1 | corrective, prise |
| PyJWT | 2.13.0 | 2.14.0 | prise ; 39 tests SSO/Keycloak/seal verts |
| jwcrypto | 1.5.8 | 1.6.0 | prise (via python-keycloak) |
| python-dotenv | 1.2.2 | 1.2.3 | prise ; scénario 0080 (`find_dotenv`) vert |
| zope.interface / zope.proxy / persistent / BTrees / zodbpickle | 8.5 / 7.2 / 6.7 / 6.4 / 4.4 | 8.6 / 7.3 / 6.8 / 6.5 / 4.5 | prises ; aller-retour ZODB §4.3 |
| anyio, charset-normalizer, idna, packaging, cffi | — | — | transitives, prises |
| coverage | 7.15.2 | 7.16.0 | prise ; 72,76 % → 72,69 %, aucune ligne perdue, plancher 68 inchangé |
| pygments, soupsieve | — | — | prises |
| ruff | 0.16.1 | 0.16.7 | prise ; CI-exact vert (règles F seules) |
| cyclonedx-python-lib, librt, filelock, platformdirs, msgpack, stevedore, pip-api, pip | — | — | transitives qualité, prises |
| greenlet | 3.5.4 | 3.5.5 | prise (e2e) |
| **mypy** | 1.20.2 | 1.20.2 | **non prise** : mypy 2.x resserre les règles par défaut, job informatif à 132 ; borne `<2` de pyproject |
| **pyee** | 13.0.1 | 13.0.1 | **non prise** : playwright 1.62.0 exige `pyee<14` |
| **setuptools** | 80.10.2 | 80.10.2 | **bloqué** (§2.2) |

Aucune borne de `pyproject.toml` n'a été modifiée : toutes les cibles sont dans les fourchettes déclarées. Hors PyPI, non traités dans ce train : digest `ubuntu:24.04` des quatre images (à rafraîchir sur kuneagi02), SHA des Actions GitHub, `validate_email` 1.3 (2015) et `pyramid_handlers` 0.5 (2012), non maintenus.

## 4. Preuves

### 4.1 Commit A — webob seul

- `pip-audit --no-deps --ignore-vuln PYSEC-2026-3447` sur les verrous précédents : 1 vulnérabilité (webob) ; sur les nouveaux : aucune, 2 ignorées.
- Diff des trois verrous : uniquement `webob==` et ses deux hachages.
- `tests/test_webob_redirect_lock.py` : 14 verts sur 1.8.11 ; webob forcé à 1.8.10 : 5 rouges (4 `Response.location` détournés + le chemin `HTTPFound`), les tests de la garde applicative restent verts.
- Suite complète sur clone vierge, Python 3.12.3 : 1086 verts, couverture 72,76 %.

### 4.2 Commit B — rattrapage

- `pip check` propre ; 1100 verts (1086 + 14), couverture 72,69 % ; ruff 0.16.7 CI-exact vert ; bandit -ll vert ; pip-audit sur les quatre verrous : aucune vulnérabilité, 2 ignorées ; mypy 132 avant et après.
- Invariants vérifiés dans les verrous : `mypy==1.20.2`, `pyee==13.0.1`, `setuptools==80.10.2`.

### 4.3 Aller-retour ZODB (le seul risque réel du train)

Un `Data.fs` de 50 membres construit avec les vrais modèles (`appmaker`, `Members`, `Member`, `MemberDatas`) par l'ancienne pile (zodbpickle 4.4, persistent 6.7, BTrees 6.4, zope.interface 8.5) : ouvert par la nouvelle pile, `run_pending_upgrades` ne trouve rien en attente, les 50 membres relus et vérifiés, un membre ajouté, un modifié, `db.pack()`, réouverture — puis le fichier compacté est relu par l'ancienne pile. **Limite** : ce n'est pas le Data.fs de kuneagi02 ; l'étape sur copie de la prod reste due avant déploiement.

### 4.4 Commit C — importlib.resources

- 1102 verts (1100 + 2) ; `grep pkg_resources` vide sur `alirpunkto/`, `tools/` et les deux scripts Docker.
- Wheel construite avec `python -m build`, installée `--no-deps` sur le verrou runtime dans un venv neuf (modèle de l'image Pyramid) : les deux répertoires de gabarits se résolvent en chemins réels, `form.pt` présent.

## 5. Ce qui n'a pas été fait ici

- Le Data.fs réel de kuneagi02 (§4.3), le build des images Docker, `smoke.yml` et `test-stack.yml` : à la CI et à Michaël.
- Les journaux CI (302 vers blob depuis le sandbox) : l'échec du 1ᵉʳ septembre est celui rapporté par la contre-expertise.
- Le digest `ubuntu:24.04` et les tags des Actions (domaines hors liste blanche du sandbox).
- Python 3.14 : retiré du chantier par décision du 12/09 ; la contre-expertise avait noté que WebOb 1.8.11 ajoute `legacy-cgi>=2.6 ; python_version>='3.13'`, donc qu'un verrou calculé sous 3.12 ne vaut pas pour 3.13+ — point à reprendre le jour de la qualification.

## 6. Déploiement

kuneagi02 : `cd ~/alirpunkto/docker && git pull && docker compose build alirpunkto-pyramid && docker compose up -d alirpunkto-pyramid`, puis `/login` et un `/modify_member` (la synchro LDAP au login, fix 0112, exerce lecture et écriture ZODB). kuneagi01 (prod historique épinglée à `e6603d22`) : ne pas toucher ; le dossier 0087 s'appliquera sur un master incluant 0113.

## Journal

- 2026-09-12 : première version de l'audit (Claude), contre-expertise ChatGPT v2 (Python 3.14 qualifié à part, `pkg_resources` importé par l'application, `legacy-cgi` conditionnel, décompte 106), décision Python 3.12, contre-expertise v3, exécution du train 0113 en trois commits et versement de cet audit.
- 2026-10-23 : suivi — six avis publiés depuis (PyJWT, urllib3, certifi) ont remis la CI qualité au rouge ; trois épingles relevées, voir [train 0116](20261023_audit_dependances_train_0116.md).
