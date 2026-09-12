# AlirPunkto — audit des dépendances et plan de mise à jour

*Audit du 12 septembre 2026, sur `master` @ `00bd677` (train 0112, 01/09/2026).*
*Méthode : lecture des quatre verrous hachés, comparaison de chaque épingle avec la dernière version stable non retirée sur PyPI, `pip-audit --no-deps` sur chaque verrou, et `pip-compile --upgrade --dry-run` pour vérifier que la résolution reste saine.*

## 1. Résumé exécutif

| | |
|---|---|
| Paquets épinglés (4 verrous, dédoublonnés) | 105 |
| À jour | 74 |
| En retard | 31 (3 majeures, 15 mineures, 13 correctives) |
| Vulnérabilités connues | **2** : `webob` 1.8.10 (nouvelle, **bloquante en CI**) et `setuptools` 80.10.2 (connue, ignorée par décision documentée) |
| Résolution pip-compile après upgrade | **Saine**, aucun conflit ; `setuptools` reste à 80.10.2 (chaîne deform/pyramid) |

**Le point urgent** : `PYSEC-2026-3943` / CVE-2026-54770 sur **WebOb 1.8.10** est sorti le 2 août. Le job `bandit + pip-audit (blocking)` de `quality.yml` n'ignore que `PYSEC-2026-3447` : **le prochain run de la CI sera rouge** sur les trois verrous. C'est une redirection ouverte via l'en-tête `Location` — exactement la classe de faille fermée côté application par le train 0063. La correction est `webob==1.8.11`, une version corrective sans changement d'API.

Tout le reste est du rattrapage de routine. Aucune version majeure ne touche le runtime : les trois majeures (`setuptools`, `mypy`, `pyee`) sont respectivement bloquée, informative, et interdite par `playwright`.

## 2. Vulnérabilités

### 2.1 WebOb 1.8.10 — PYSEC-2026-3943 (CVE-2026-54770, GHSA-6hx8-3wjj-gr8g) — **P0**

- Troisième suite de CVE-2024-42353 / CVE-2026-44889. WebOb absolutise l'en-tête `Location` d'une redirection ; le filtrage des cibles relatives-protocole (`//hôte`) était contournable parce qu'`urllib.parse.urljoin()` retire, sur Python ≥ 3.10, plus de caractères que le correctif précédent ne le supposait.
- Exposition AlirPunkto : Pyramid s'appuie sur WebOb pour toute `HTTPFound`. Le train 0063 a fermé la redirection ouverte *applicative* (paramètre `next`) ; cette CVE vit **sous** cette couche, dans la sérialisation de l'en-tête. La garde 0063 réduit l'exposition sans l'annuler.
- Correctif : `webob==1.8.11` (02/08/2026), corrective pure, présente dans les trois verrous (`via pyramid`).

### 2.2 setuptools 80.10.2 — PYSEC-2026-3447 (CVE-2026-59890) — **inchangé, à documenter**

- Toujours bloqué sous 81 : `deform 3.0.1` déclare `setuptools<81.0.0`, `pyramid 2.1` déclare `setuptools<82`. Le correctif est 83.0.0 ; la dernière est 84.0.0. **Aucune des deux chaînes n'a bougé** depuis l'ignore d'août.
- La CVE concerne la construction de sdist sur macOS (normalisation Unicode de `MANIFEST.in`) : hors du chemin d'exécution, hors de l'image Docker. L'ignore reste justifié.
- Action : ne rien changer, mais **dater la réévaluation** dans le commentaire de `quality.yml` (voir §5, étape 6).

## 3. Inventaire des retards

Légende : R = requirements.lock (image Docker), T = -test, Q = -quality, E = -e2e.

### 3.1 Runtime (R, T, Q) — 16 paquets

| Paquet | Épinglé | Dernière | Date | Saut | Note |
|---|---|---|---|---|---|
| **webob** | 1.8.10 | **1.8.11** | 02/08 | corrective | **CVE, voir §2.1** |
| cryptography | 50.0.0 | 50.0.1 | 25/08 | corrective | pas de vulnérabilité sur 50.0.0 ; borne `>=50,<51` déjà bonne |
| pyjwt | 2.13.0 | 2.14.0 | 11/09 | mineure | sorti hier ; touche `_validated_token_payload` (SSO) → tests SSO à surveiller |
| jwcrypto | 1.5.8 | 1.6.0 | 01/09 | mineure | via python-keycloak (`>=1.5.4`) |
| python-dotenv | 1.2.2 | 1.2.3 | 16/08 | corrective | **attention** : 0080 (`find_dotenv(usecwd=True)`) repose sur le frame-walk de dotenv — vérifier le changelog avant de monter |
| zope.interface | 8.5 | 8.6 | 20/08 | mineure | train Zope coordonné du 20/08 |
| zope.proxy | 7.2 | 7.3 | 20/08 | mineure | idem |
| persistent | 6.7 | 6.8 | 20/08 | mineure | idem |
| BTrees | 6.4 | 6.5 | 20/08 | mineure | idem |
| zodbpickle | 4.4 | 4.5 | 20/08 | mineure | idem — **format de pickle : le Data.fs de prod doit rester lisible** (voir §5, étape 3) |
| anyio | 4.14.2 | 4.15.1 | 05/09 | mineure | via httpx |
| charset-normalizer | 3.4.9 | 3.5.1 | 15/08 | mineure | via requests |
| idna | 3.18 | 3.19 | 18/08 | mineure | via requests |
| packaging | 26.2 | 26.3 | 04/08 | mineure | |
| cffi | 2.1.0 | 2.1.1 | 03/08 | corrective | via cryptography |
| setuptools | 80.10.2 | 84.0.0 | 08/08 | **majeure** | **bloqué** (§2.2) |

`ZODB` 6.3, `ZEO` 6.2, `transaction` 5.1, `pyramid` 2.1, `waitress` 3.0.2, `deform` 3.0.1, `ldap3` 2.9.1, `bcrypt` 5.0.0, `requests` 2.34.2, `python-keycloak` 7.1.1 : **à jour**.

### 3.2 Test (T) — 3 paquets

| Paquet | Épinglé | Dernière | Saut |
|---|---|---|---|
| coverage | 7.15.2 | 7.16.0 | mineure — seuil `cov≥68` à revérifier (le calcul des branches peut bouger) |
| pygments | 2.20.0 | 2.21.0 | mineure |
| soupsieve | 2.9.1 | 2.9.2 | corrective |

`pytest` 9.1.1, `pytest-cov` 7.1.0, `WebTest` 3.0.7, `beautifulsoup4` 4.15.0 : à jour.

### 3.3 Qualité (Q) — 10 paquets

| Paquet | Épinglé | Dernière | Saut | Note |
|---|---|---|---|---|
| **mypy** | 1.20.2 | **2.3.1** | **majeure** | job informatif (~130 erreurs) ; mypy 2 resserre plusieurs règles par défaut → le compteur montera. Borne `<2` dans pyproject : **ne pas franchir dans ce train** |
| ruff | 0.16.1 | 0.16.7 | corrective | seules les règles F sont actives, stables ; risque faible mais lancer le CI-exact |
| cyclonedx-python-lib | 11.11.0 | 11.12.0 | mineure | via pip-audit |
| librt | 0.13.0 | 0.15.0 | mineure | via mypy |
| filelock | 3.32.2 | 3.32.6 | corrective | |
| platformdirs | 4.11.0 | 4.11.8 | corrective | |
| msgpack | 1.2.1 | 1.2.2 | corrective | |
| stevedore | 5.9.0 | 5.9.1 | corrective | via bandit |
| pip-api | 0.0.34 | 0.0.35 | corrective | |
| pip | 26.2 | 26.2.1 | corrective | |

`bandit` 1.9.4, `pip-audit` 2.10.1 : à jour.

### 3.4 E2E (E) — 2 paquets

| Paquet | Épinglé | Dernière | Saut | Note |
|---|---|---|---|---|
| pyee | 13.0.1 | 14.0.0 | majeure | **interdit** : playwright 1.62.0 exige `pyee<14,>=13`. Rien à faire |
| greenlet | 3.5.4 | 3.5.5 | corrective | |

`playwright` 1.62.0 : à jour.

### 3.5 Hors PyPI (non couvert par pip-audit)

- **Images de base** : les quatre Dockerfiles épinglent `ubuntu:24.04@sha256:4fbb8e6a…`. Un digest est immuable : les correctifs de sécurité d'apt (openssl, slapd, postfix, apache2, certbot) n'entrent qu'en ré-épinglant. À rafraîchir (`docker pull ubuntu:24.04` puis `docker image inspect --format '{{index .RepoDigests 0}}'`) — hors de portée du sandbox, à faire sur kuneagi02.
- **Actions GitHub** épinglées par SHA (`actions/checkout`, `setup-python`, …) : non vérifiées ici (API GitHub anonyme rate-limitée). À passer en revue avec Dependabot ou `pinact` dans un train séparé.
- **Matrice Python** : CI sur 3.11/3.12, image sur 3.12 (Ubuntu 24.04). Toute la pile déclare `>=3.10`. Ajouter 3.13 en job **informatif** serait peu coûteux et préparerait la sortie de 3.11 du support (octobre 2027).

## 4. Résolution vérifiée

`pip-compile --allow-unsafe --strip-extras --upgrade --dry-run -o requirements.lock pyproject.toml` (sans hachages, pour la vitesse) produit exactement les 16 montées du §3.1, **rien d'autre ne bouge**, et `setuptools` reste à 80.10.2 comme attendu. Aucune borne de `pyproject.toml` n'a besoin d'être modifiée : toutes les cibles sont déjà dans les fourchettes déclarées.

## 5. Plan de mise à jour — train 0113

Un seul train, deux commits, pour que le premier puisse être cherry-pické seul si le second révèle un problème.

### Étape 0 — préparation (clone vierge, comme d'habitude)

```bash
git clone git@github.com:michaellaunay/alirpunkto.git ap-0113 && cd ap-0113
git config pull.ff only
python3.12 -m venv venv && . venv/bin/activate
pip install --upgrade pip pip-tools
sudo apt-get install -y gettext          # pour les .mo si le harnais est neuf
```

Garder une copie des quatre verrous actuels dans `/tmp` (démonstration rouge/vert de l'étape 6).

### Étape 1 — commit A : `webob` seul (hotfix CI, P0)

Regénérer les trois verrous **sans** `--upgrade` global, en ne libérant que webob :

```bash
for spec in "" "--extra testing" "--extra quality"; do
  out=requirements$( [ -n "$spec" ] && echo "-${spec#--extra }" | sed 's/-testing/-test/' ).lock
  pip-compile --allow-unsafe --generate-hashes --strip-extras \
      --upgrade-package webob $spec -o "$out" pyproject.toml
done
```

Preuve rouge/vert :

```bash
pip-audit --no-deps --ignore-vuln PYSEC-2026-3447 -r /tmp/requirements.lock      # rouge : webob 1.8.10
pip-audit --no-deps --ignore-vuln PYSEC-2026-3447 -r requirements.lock           # vert
```

Diff attendu : **uniquement** les lignes `webob==` et leurs deux hachages dans chacun des trois verrous. Tout autre changement signale un problème de graine.

Commit (convention du projet, anglais, Conventional) :

```
fix(deps): bump webob to 1.8.11 for the Location-header open redirect

Problem: PYSEC-2026-3943 (CVE-2026-54770, GHSA-6hx8-3wjj-gr8g) …
Fix: …
Proof: pip-audit red on the previous locks, green on the new ones; …

Refs: PYSEC-2026-3943
```

### Étape 2 — commit B : rattrapage de routine (tout le §3 sauf mypy/pyee/setuptools)

```bash
pip-compile --allow-unsafe --generate-hashes --strip-extras --upgrade \
    -o requirements.lock pyproject.toml
pip-compile --allow-unsafe --generate-hashes --strip-extras --upgrade \
    --extra testing -o requirements-test.lock pyproject.toml
pip-compile --allow-unsafe --generate-hashes --strip-extras --upgrade \
    --extra quality --upgrade-package 'mypy<2' -o requirements-quality.lock pyproject.toml
pip-compile --allow-unsafe --generate-hashes --strip-extras --upgrade \
    -o requirements-e2e.lock requirements-e2e.in
```

`mypy` reste sous 2 par la borne de `pyproject.toml` (`>=1.14,<2`) ; la mention explicite ci-dessus est une ceinture. Vérifier dans le diff que `mypy==1.20.2` et `pyee==13.0.1` sont **inchangés** et que `setuptools==80.10.2` l'est aussi.

### Étape 3 — vérifications ciblées (les seuls risques réels du train)

1. **Lecture du Data.fs** après `zodbpickle` 4.5 / `persistent` 6.8 / `BTrees` 6.5 : sur une copie du `Data.fs` de kuneagi02, `tools/run_upgrades.py --dry-run` (ou un simple `ZODB.DB(FileStorage).open().root()` avec parcours des membres) doit passer. Rien dans les changelogs Zope du 20/08 n'annonce de rupture de format, mais c'est la preuve qu'il faut avant la prod.
2. **`python-dotenv` 1.2.3** : relancer le scénario 0080 — `pserve production.ini` depuis le conteneur (wheel non-editable, `.env` hors du paquet) doit trouver le `.env`. Le test qui couvre `find_dotenv(usecwd=True) or find_dotenv()` doit rester vert.
3. **`PyJWT` 2.14.0** : `pytest tests -k 'sso or keycloak or token'` — `seal_sso_refresh_token` et `_validated_token_payload` ; les tests « oversized » sur données incompressibles restent la référence.
4. **`coverage` 7.16** : le seuil `--cov-fail-under=68` de `tests.yml` ; si la mesure baisse de quelques dixièmes par changement de comptage, **ne pas abaisser le seuil** — noter l'écart dans CHANGES.txt et laisser la marge existante absorber.

### Étape 4 — suite complète

```bash
pip install -r requirements-test.lock --require-hashes && pip install -e . --no-deps
pytest                                                             # 1086 verts attendus (0112)
ruff check alirpunkto tests tools docker/apply_server_overrides.py docker/generate_ldif.py
bandit -ll -r alirpunkto
pip-audit --no-deps --ignore-vuln PYSEC-2026-3447 -r requirements.lock -r requirements-test.lock -r requirements-quality.lock
mypy alirpunkto | tail -1                                          # ~130, informatif — noter le chiffre
```

Puis, sur la pile de test locale (`docker/test-docker-compose.yaml`) : build de l'image Pyramid (les trois sdist purs du `DockerfilePyramid` ne sont pas concernés), `smoke.yml` en local si possible, sinon laisser la CI le prouver.

### Étape 5 — commit B

```
chore(deps): refresh the four hashed locks (September 2026)

Problem: 30 pins behind upstream since the August regeneration …
Fix: pip-compile --upgrade on the four locks; mypy stays <2 (informative
job, 2.x tightens defaults), pyee stays 13 (playwright <14), setuptools
stays 80.10.2 (deform <81, pyramid <82).
Proof: 1086 tests green on a fresh clone, ruff CI-exact green, pip-audit
green with the documented ignore, Data.fs from kuneagi02 opens read-only
under zodbpickle 4.5 …

Refs: 0113
```

### Étape 6 — dossier (même train)

- `quality.yml` : compléter le commentaire de l'ignore `PYSEC-2026-3447` : *« Réévalué le 2026-09-12 : deform 3.0.1 `<81`, pyramid 2.1 `<82`, correctif en 83 ; prochaine revue à la sortie de deform 3.1 ou pyramid 2.2 »*.
- `CHANGES.txt` : bloc `Unreleased (2026-09-12)` — deux entrées (CVE webob ; rattrapage), dans le style des blocs existants.
- `docs/fr/audits/20260912-dependances.md` + miroir `docs/en/audits/` (traduction intégrale, selon la convention) : ce document, avec le chapeau « chaîne des audits » habituel.
- `docs/fr/04-…` (exploitation) : note sur le rafraîchissement du digest `ubuntu:24.04` (voir §3.5) — geste kuneagi02, hors dépôt Python.

### Étape 7 — déploiement

- **kuneagi02** (instance neuve) : `cd ~/alirpunkto/docker && git pull && docker compose build alirpunkto-pyramid && docker compose up -d alirpunkto-pyramid`, puis vérifier `/login` et un `/modify_member` (le fix 0112 dépend de la synchro LDAP au login — bon test de non-régression ZODB).
- **kuneagi01** (vraie prod, épinglée à `e6603d22`, en attente de validation client) : **ne pas toucher**. Quand la migration sera validée, le dossier 0087 s'appliquera sur un `master` qui inclura 0113 ; l'étape 3.1 aura déjà prouvé la compatibilité du Data.fs.

## 6. Hors train — à planifier séparément

| Sujet | Quand | Pourquoi séparé |
|---|---|---|
| Digest `ubuntu:24.04` des 4 images | dès que possible, sur kuneagi02 | geste d'exploitation, rebuild complet des 4 conteneurs, à faire à froid |
| SHA des Actions GitHub | prochain train CI | Dependabot `github-actions` ou `pinact` ; indépendant du code |
| mypy 2.x | quand le compteur informatif sera sous ~50 | mypy 2 resserre les règles par défaut ; passer d'abord le cliquet mypy prévu au carnet |
| Python 3.13 en job informatif | train CI | prépare la fin de vie de 3.11 (10/2027) ; la pile Zope déclare `>=3.10` |
| Remplacement de `validate_email` 1.3 (2015) et `pyramid_handlers` 0.5 (2012) | dette | non maintenus depuis dix ans ; pas de CVE, mais aucun correctif n'arrivera. Candidats : `email-validator` ; `pyramid_handlers` est trivial à internaliser |
| `pyramid_mailer` 0.15.1 (2016) / `repoze.sendmail` | dette | même constat ; `repoze.sendmail` 4.5 est lui à jour |

## 7. Ce que je n'ai pas pu vérifier depuis le sandbox

- Les journaux de la CI (302 vers blob) — donc je n'ai pas *vu* le job pip-audit rouge ; je le déduis de `quality.yml` et de la sortie de `pip-audit` sur les verrous actuels.
- Les digests Docker Hub et les tags des Actions (domaines hors liste blanche).
- La lecture réelle d'un Data.fs de prod (étape 3.1) — c'est à toi, sur une copie.
