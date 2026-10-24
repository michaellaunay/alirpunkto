# Suivi de l'audit des dépendances — train 0116 (octobre 2026)

**Date** : 2026-10-23 · **Auditeur** : Claude (assistant de développement) · **Référence** : master `023d2c77` (train 0115) · **Dossier parent** : [audit des dépendances et train 0113](20260912_audit_dependances_train_0113.md) · **Décision** : relever trois épingles, rien d'autre.

## 1. Constat

Le workflow `quality` est rouge sur les deux commits du 20 octobre (`d8d8c9cb`, `023d2c77`) alors que `Tests`, `smoke` et `test-stack` sont verts. Les commits ne sont pas en cause : le job `pip-audit (blocking)` échoue sur des avis publiés entre le dernier run vert (12 septembre) et le 20 octobre, et un troisième paquet s'est ajouté depuis. Le job `mypy (informative)` apparaît rouge (133 erreurs) mais reste `continue-on-error` : il n'a jamais fait échouer le workflow.

| Paquet | Épingle | Avis | Correctif | Pris |
|---|---|---|---|---|
| PyJWT | 2.14.0 | PYSEC-2026-4141 / CVE-2026-101918 (`RecursionError` sur un payload JSON profondément imbriqué, échappe à `PyJWTError`) ; PYSEC-2026-4183 / CVE-2026-102275 (`OKPAlgorithm.from_jwk` ne vérifie pas `d` contre `x`) | 2.15.0 | **2.15.1** (28/09) |
| urllib3 | 2.7.0 | PYSEC-2026-4175 / CVE-2026-97687 (réglages TLS du proxy écrasés par ceux de la cible) ; PYSEC-2026-4176 / CVE-2026-97688 (boucle infinie sur octets résiduels après un flux Deflate) ; PYSEC-2026-4177 / CVE-2026-97689 (champ taille de chunk non borné en streaming) | 2.8.0 | **2.8.0** (15/09) |
| certifi | 2026.7.22 | PYSEC-2026-4320 / GHSA-6q48-6c7w-9gw2 (racine `emSign ECC Root CA - G3`, intermédiaires eMudhra aux clés compromises) | 2026.10.19 | **2026.10.23** (23/10) |

Exposition réelle : `views/sso_login.py` appelle `jwt.decode` avec vérification de signature, donc le chemin du payload imbriqué n'est atteignable qu'avec un jeton frappé par le canal arrière Keycloak ; urllib3 et certifi portent les appels `requests`/`python-keycloak` vers Keycloak. Faible, mais la porte CI est bloquante par construction (décision du 4ᵉ passage externe).

## 2. Correctif

`pip-compile --upgrade-package pyjwt --upgrade-package urllib3 --upgrade-package certifi` sur chacun des trois verrous, semé par le verrou précédent : le diff ne contient que les trois épingles et leurs hachages. L'en-tête perd `--no-index`, trace du bac à sable sans PyPI de septembre (wheelhouse locale) ; la résolution s'est faite ici contre PyPI. Le verrou e2e ne porte aucun des trois paquets et reste intact.

`tests/test_october_2026_cve_floors.py` verrouille deux couches : le reproducteur PYSEC-2026-4141 contre la bibliothèque (un payload imbriqué 10 000 niveaux doit lever un `PyJWTError`, pas un `RecursionError` nu), l'absence de la racine emSign compromise dans le bundle certifi, et un plancher par paquet et par verrou.

## 3. Preuves

- Rouge sur l'état précédent (verrous et bibliothèques de septembre) : 11 échecs (2 bibliothèque + 9 planchers) ; vert après : 11.
- Suite complète : 1166 verts (1155 + 11), couverture 74,07 %, plancher 68 inchangé.
- Portes CI-exactes : ruff vert, bandit `-ll` vert, `pip-audit --no-deps --ignore-vuln PYSEC-2026-3447` sur les trois verrous : aucune vulnérabilité, 2 ignorées ; verrou e2e : aucune.
- Aucune borne de `pyproject.toml` modifiée (`PyJWT>=2.7.0,<3`, `requests>=2.33.1,<3`).

## 4. Non traité ici

- mypy : 133 erreurs informatives (132 en septembre), job non bloquant, hors périmètre.
- setuptools 80.10.2 / PYSEC-2026-3447 : toujours bloqué par deform 3.0.1 et pyramid 2.1 (§2.2 du dossier 0113), ignore conservé.
- Les images Docker embarquent certifi via le verrou runtime : reconstruire `alirpunkto-pyramid` sur kuneagi02 au déploiement (l'avis certifi le demande explicitement).

## 5. Suivi du 24 octobre — train 0118

Le workflow `quality` est retombé au rouge sur `34a224f7` et `38dedcf7` : deux nouveaux avis publiés après le calcul des verrous du 0116.

| Paquet | Épingle | Avis | Correctif | Décision |
|---|---|---|---|---|
| filelock | 3.32.6 (verrou qualité seul, via cachecontrol sous pip-audit) | CVE-2026-112907 / 112913 / 112940 (verrous SQLite et verrous souples détournables par un autre compte local) | 4.2.1 | **4.2.4** (19/10), `pip-compile --upgrade-package filelock` sur le seul verrou qualité ; plancher `>= 4.2.1` dans `tests/test_october_2026_cve_floors.py` |
| setuptools | 80.10.2 | GHSA-xmj3-9gf7-h52w (chemin d'installation `Wheel.install_as_egg`, Windows, `namespace_packages.txt` d'une wheel hostile) | 84.1.0 | **ignore daté** dans `quality.yml`, même chaîne et même classe que PYSEC-2026-3447 : deform 3.0.1 (`setuptools<81`) et pyramid 2.1 (`<82`) sont toujours les dernières versions sur PyPI au 24/10 ; les deux ignores se lèveront ensemble |

`AGENTS.md` cite la nouvelle commande verbatim (`tests/test_agent_harness.py` l'exige) et un test vérifie que chaque ignore porte sa date de revue.

## Journal

- 2026-10-23 : diagnostic des deux runs rouges, relevé des trois épingles, test de verrouillage, versement de cette note.
- 2026-10-24 : suivi (§5) — filelock relevé dans le verrou qualité, second ignore setuptools daté, train 0118.
