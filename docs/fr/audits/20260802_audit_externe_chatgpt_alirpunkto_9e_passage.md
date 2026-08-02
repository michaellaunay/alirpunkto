# Audit externe du dépôt (ChatGPT), neuvième passage — 2 août 2026

**Provenance.** Neuvième passage de l'audit statique externe (ChatGPT,
à la demande de Michaël Launay), sur le commit `72e65db2` (finition
d'image) ; passage précédent sur `2bc56291`. Note globale proposée :
**8,4/10** — en baisse. Au fil des passages : 6,5 → 6,9 → 6,7 → 7,1 →
7,8 → 8,2 → 8,5 → 8,6 → 8,4. Texte transmis a posteriori (le
2026-08-02) et versé pour l'archive : ce document décrit l'état après
le train 0075 — **c'est ici que la double clé `args:` du service LDAP
a été signalée pour la première fois**, mais le texte n'ayant pas été
transmis à l'époque, c'est le dixième passage qui l'a portée jusqu'à
nous ; le correctif (0078) est arrivé deux passages plus tard qu'il
n'aurait dû.

**Statut (rétrospectif).** L'audit valide la finition d'image (wheel,
parité réelle, only-binary avec exceptions nommées, zéro compilateur,
copie en liste blanche, snapshot APT) et confirme la casse latente du
helper d'overrides — en notant, honnêteté appréciable, que ses propres
passages précédents « avaient validé le câblage par inspection sans
vérifier la composition effective du contexte Docker ». Il découvre en
retour la régression P0 que ce même train a introduite (double clé
`args:`) — corrigée en 0078 avec la porte `compose config --quiet`
qu'il prescrivait mot pour mot. Deux suggestions retenues au carnet :
**vérifier structurellement la pureté des trois exceptions sdist** (le
test pourrait construire chaque wheel et refuser tout tag autre que
`py3-none-any`) et **une image de test autonome** (l'installation
dynamique du verrou de test au démarrage rend la pile locale
dépendante de l'index).

## Suites données

0078 (fusion des blocs `args`, porte compose, émetteur commun,
tests des appelants) — chronique dans les versements des 10ᵉ et 11ᵉ
passages.

# Texte intégral de l'audit (neuvième passage)

# Audit actualisé du dépôt AlirPunkto — neuvième passage

**Date :** 2 août 2026
**Dépôt :** `michaellaunay/alirpunkto`
**Branche :** `master`
**Commit examiné :** `72e65db2de566bc193c5d14130ac301594b4231a`
**Audit précédent :** `2bc562912856a20a777d38b748bece8b41916c97`

## 1. Résumé exécutif

Le nouveau commit améliore nettement la fabrication de l'image
Pyramid :

* installation de l'application sous forme de wheel non éditable ;
* suppression complète de l'arbre source dans l'image finale ;
* obligation d'utiliser des distributions binaires, sauf trois exceptions Python pur explicitement nommées ;
* suppression des compilateurs et en-têtes de développement, y compris dans le builder ;
* copie runtime limitée à une liste explicite ;
* ajout d'un mode reproductible APT fondé sur les snapshots Ubuntu ;
* adaptation de la pile de tests à l'image sans sources ;
* vérification de la complétude réelle de la wheel.

Il corrige également un blocage Docker latent qui invalide une
conclusion de l'audit précédent : `start_pyramid.sh` appelait
`docker/apply_server_overrides.py`, mais `.dockerignore` excluait tout
le répertoire `docker/`. Le helper ne pouvait donc pas atteindre
l'image. Docker retire les chemins ignorés du contexte avant de
l'envoyer au builder ; une instruction `COPY` ne peut utiliser qu'un
fichier présent dans ce contexte.

Le helper est maintenant explicitement réintégré dans le contexte et
explicitement copié dans l'image finale.

Cependant, le commit introduit simultanément une nouvelle régression
P0 dans le Compose de production : le service LDAP contient deux clés
`args:` au même niveau.

```yaml
build:
  context: .
  dockerfile: DockerfileOpenLDAP
  args:
    UBUNTU_SNAPSHOT: ${ALIRPUNKTO_UBUNTU_SNAPSHOT:-}
  args:
    BUILD_WITH_DEBUG: ${BUILD_WITH_DEBUG:-0}
```

Les clés d'une structure YAML doivent être uniques. Le fichier est
donc invalide selon la spécification YAML ; un parseur strict doit le
refuser, tandis qu'un parseur permissif risque d'écraser le premier
bloc. Dans le second cas, `UBUNTU_SNAPSHOT` ne serait pas transmis à
l'image LDAP. Dans le premier cas, toute la pile de production serait
impossible à lancer.

Le message de commit annonce 1 009 tests réussis avec 72,10 % de
couverture, mais aucun workflow ni statut GitHub Actions n'est
retourné pour ce SHA. Le commit précise lui-même que le Docker daemon
n'était pas disponible dans son environnement de construction. Ces
résultats restent donc non confirmés par une exécution end-to-end.

## 2. Évaluation actualisée

| Domaine                           | Note précédente | Nouvelle note |
| --------------------------------- | --------------: | ------------: |
| Architecture applicative          |             7,8 |           7,9 |
| Qualité du code                   |             8,0 |           8,1 |
| Tests                             |             9,2 |           9,1 |
| CI et contrôles automatiques      |             9,0 |           8,8 |
| Documentation                     |             8,0 |           8,0 |
| Dépendances et reproductibilité   |             9,0 |           9,4 |
| Sécurité applicative              |             8,8 |           8,8 |
| Sécurité et fonctionnement Docker |             9,1 |           7,9 |
| Exploitation et observabilité     |             7,4 |           7,5 |

**Note globale actualisée : 8,4/10**, contre 8,6/10 précédemment.

Les améliorations de l'image sont excellentes, mais elles ne
compensent pas entièrement la présence d'un fichier Compose de
production invalide.

# 3. Blocage latent du helper Docker — résolu

## 3.1 Problème antérieur

Depuis le train Docker P0, le script de démarrage exécute
`python3 "${APP_DIR}/docker/apply_server_overrides.py" …` lorsque
`PYRAMID_LISTEN` ou `PYRAMID_TRUSTED_PROXY` est défini. Compose
définit ces variables par défaut. Pourtant, l'ancien `.dockerignore`
excluait `docker/`, à l'exception du seul script de démarrage.

Le conteneur aurait donc échoué avant le lancement de `pserve`.

Cette faiblesse n'avait pas été repérée lors du passage précédent, qui
avait validé le câblage par inspection sans vérifier la composition
effective du contexte Docker.

## 3.2 Correction actuelle

Le fichier `.dockerignore` contient désormais la réintégration
`!docker/apply_server_overrides.py` et le Dockerfile ajoute une copie
explicite du helper dans l'image.

**Statut : résolu par inspection.**

**Limite du test.** Le test actuel vérifie uniquement la présence
textuelle de la règle de réintégration et de l'instruction `COPY`. Il
ne construit pas réellement le contexte Docker et ne vérifie pas que
le fichier est reçu par BuildKit. Le smoke test réel reste donc
indispensable.

# 4. Régression P0 : double clé args dans Compose

Le service LDAP de `docker/docker-compose.yaml` contient deux clés
`args:` consécutives dans le même mapping. Une structure YAML est un
ensemble de paires dont les clés doivent être uniques.

**Conséquences possibles.**

*Parseur strict* : `docker compose --env-file docker/.env -f
docker/docker-compose.yaml config` échoue avant toute construction. La
pile ne peut alors pas démarrer.

*Parseur permissif* : le second bloc `args` remplace le premier —
`UBUNTU_SNAPSHOT` n'est plus transmis à OpenLDAP.

Dans les deux cas, le résultat est incorrect.

**Correction nécessaire.** Fusionner les deux blocs :

```yaml
args:
  BUILD_WITH_DEBUG: ${BUILD_WITH_DEBUG:-0}
  UBUNTU_SNAPSHOT: ${ALIRPUNKTO_UBUNTU_SNAPSHOT:-}
```

**Contrôle CI à ajouter.** Avant toute construction Docker, valider
les deux fichiers Compose avec `docker compose … config --quiet`.

**Statut : ouvert, P0.**

# 5. Installation de l'application sous forme de wheel — résolu

L'application n'est plus installée en mode éditable. Le builder
exécute maintenant `pip install --no-cache-dir --no-build-isolation
--no-deps .`. Le virtualenv installé est copié dans l'étape finale.
L'arbre source n'est plus nécessaire à l'exécution.

Le script de démarrage ne recherche plus `pyproject.toml` ou une
arborescence applicative. Il vérifie directement
`"${VENV_DIR}/bin/python" -c "import alirpunkto"`.

**Statut : résolu.**

# 6. Complétude de la wheel — correctement testée

Une installation par wheel peut fonctionner à l'import tout en étant
inutilisable si elle omet des templates Chameleon, des catalogues de
traduction, des schémas LDAP ou d'autres fichiers de données.

Le nouveau test : 1. construit la wheel réelle ; 2. ouvre son archive
ZIP ; 3. récupère les fichiers suivis par Git sous `alirpunkto/` ;
4. exige que chaque fichier suivi apparaisse dans la wheel.

Cette vérification est nettement plus fiable qu'un simple test
d'import.

**Statut : résolu.**

**Réserve légère.** Le test vérifie les fichiers suivis par Git, pas
les fichiers générés ou nécessaires mais oubliés du dépôt. Il reste
néanmoins adapté au risque principal.

# 7. Distributions binaires imposées — largement résolu

Les dépendances sont installées avec `--only-binary=:all:
--no-binary=pyramid-chameleon,pyramid-handlers,validate-email`. Toute
nouvelle dépendance uniquement disponible comme archive source
provoquera donc un échec explicite, sauf si elle est ajoutée à la
liste autorisée.

Les trois exceptions actuelles sont décrites comme des paquets Python
purs produisant des wheels `py3-none-any`.

Les tests vérifient : la présence de `--only-binary=:all:` ;
l'identité exacte des exceptions ; la présence effective de chaque
exception dans le verrou runtime ; l'absence de compilateur et de
paquet `*-dev`.

**Statut : résolu pour l'état actuel.**

**Réserve.** La nature « Python pur » des trois exceptions est
affirmée dans le code et le commit, mais elle n'est pas validée
structurellement dans le test. Le test pourrait construire chaque
wheel et refuser une wheel spécifique à une plateforme, une wheel
contenant une bibliothèque native, ou un tag autre que `py3-none-any`.

# 8. Compilateurs supprimés de toutes les étapes — résolu

Le builder n'installe plus `build-essential`, `python3-dev`, les
en-têtes LDAP et SSL, ni les bibliothèques de développement XML et
images. Il ne contient plus que Python, `python3-venv` et les
certificats d'autorité. Le runtime conserve uniquement Python et les
certificats, hors outils de diagnostic activés explicitement.

**Statut : résolu.**

# 9. Copie runtime limitée — résolu

L'étape finale ne fait plus de `COPY .`. Elle copie seulement le
virtualenv, `production.ini`, `.env.example`,
`apply_server_overrides.py` et `start_pyramid.sh`. Le contexte exclut
désormais aussi `.github/`, `requirements-test.lock`,
`requirements-quality.lock`, `development.ini`, les tests, les outils
et la documentation.

**Statut : résolu.**

# 10. Installation de dépendances au démarrage

**Production — résolu.** `start_pyramid.sh` n'exécute plus aucune
installation pip. L'image lance exactement le contenu construit.

**Pile de tests — toujours dynamique.** `start_test_pyramid.sh`
installe encore le verrou de tests au démarrage lorsque
`INSTALL_EXTRAS_TESTING=true`. Le verrou est monté en lecture seule
depuis l'hôte. C'est acceptable pour un environnement de
développement, mais cela signifie que le démarrage nécessite un accès
à l'index Python, que le résultat dépend de la disponibilité des
artefacts, que le healthcheck attend la fin de l'installation et que
le test de conteneur n'est pas entièrement autonome. Une image dédiée
test construite depuis un stage Docker séparé serait plus
déterministe.

# 11. Snapshots Ubuntu — mécanisme correct, câblage incomplet

Chaque Dockerfile propose maintenant `ARG UBUNTU_SNAPSHOT=""`. Lorsque
la valeur est renseignée, le fichier deb822 reçoit
`Snapshot: YYYYMMDDTHHMMSSZ`. Ubuntu 24.04 prend en charge cette
option ; les identifiants de snapshot utilisent bien le format
`YYYYMMDDTHHMMSSZ`.

Le mode reste volontairement facultatif : vide, dépôts Ubuntu
courants ; défini, état de l'archive à l'instant choisi.

**Limite actuelle.** À cause de la double clé `args`, le snapshot
n'est pas correctement câblé pour le service LDAP de production. Le
mécanisme est donc correctement implanté dans les Dockerfiles,
correctement câblé dans la pile de tests, incorrectement câblé dans le
Compose de production.

**Statut global : partiellement résolu.**

# 12. Tests du train d'image

Dix nouveaux contrôles statiques et semi-dynamiques vérifient :
l'installation non éditable ; la politique binaire ; l'absence de
compilateurs ; la copie runtime en liste blanche ; le contexte Docker
réduit ; la présence du helper ; le mécanisme de snapshot ; l'absence
de pip runtime en production ; le montage du verrou de tests ; la
parité réelle de la wheel.

Ces tests sont utiles, mais ils n'analysent pas véritablement la
structure YAML. Le contrôle du snapshot se limite à rechercher la
chaîne `ALIRPUNKTO_UBUNTU_SNAPSHOT` dans le fichier Compose. Il ne
détecte donc pas : une clé YAML dupliquée ; un argument placé dans le
mauvais service ; un argument écrasé ; une erreur d'indentation ; un
Compose impossible à parser.

**Statut : couverture structurelle insuffisante pour Compose.**

# 13. Constats précédents toujours ouverts

**13.1 Réconciliation LDAP.** Les réserves du passage précédent
restent valides : les retours d'échec de la première écriture ne
conditionnent pas la seconde ; l'union des deux côtés peut restaurer
un rôle ou une sanction obsolète ; le scan effectue de nombreuses
recherches par membre.

**13.2 Transport LDIF.** Les mots de passe et les principales données
de profil ont quitté `argv`, mais d'autres données personnelles y
restent : pseudonymes, UUID, rôles, langues, nationalités. Une
interface JSON par entrée standard ou fichier 0600 reste préférable.

**13.3 Mot de passe LDIF absent.** Une variable de mot de passe
absente peut encore être remplacée par une chaîne vide puis hachée.

**13.4 LDAP chiffré.** Les certificats LDAPS sont validés lorsque
LDAPS est activé, mais la pile fournie utilise toujours LDAP en clair
par défaut.

**13.5 Rappels périodiques.** Les rappels restent déclenchés dans
`NewRequest`.

**13.6 .env.example.** Les noms `MAIL_USE_TLS` et `MAIL_USE_SSL`
restent incompatibles avec les variables réellement lues, et
`LDAP_CA_CERT_FILE` n'est pas documenté.

**13.7 Dette qualité.** mypy non bloquant ; Ruff limité aux règles F
avec `F841` ignorée ; couverture minimale à 68 % ; Certbot et CSP non
couverts.

# 14. Priorités révisées

**P0 — rouvert.** Corriger le Compose de production : fusionner
immédiatement les deux blocs `args` du service LDAP, puis ajouter une
validation obligatoire `docker compose … config --quiet` précédant la
construction et le smoke test.

**P1 — image presque achevée.** Résolus : wheel non éditable ;
contexte runtime minimal ; absence de compilateurs ; dépendances
binaires imposées ; snapshot APT disponible ; helper réellement copié.
À compléter : 1. exécuter enfin le smoke test Docker dans GitHub
Actions ; 2. construire une image de tests autonome ; 3. vérifier que
les exceptions sdist produisent réellement des wheels universelles ;
4. rendre le snapshot obligatoire pour les builds de publication.

**P2 — sécurité applicative.** 1. terminer la cohérence
transactionnelle des groupes ; 2. retirer toutes les données
personnelles de `argv` ; 3. refuser les mots de passe absents ;
4. activer et tester LDAPS dans Compose.

**P3 — exploitation.** 1. sortir les rappels du cycle HTTP ;
2. corriger `.env.example` ; 3. optimiser le scan LDAP ; 4. tester le
renouvellement Certbot ; 5. activer et tester une CSP.

# 15. Conclusion

Le commit `72e65db…` apporte une excellente finition à l'image
Pyramid : wheel installée proprement ; sources absentes du runtime ;
contexte réduit ; compilateurs supprimés ; stratégie binaire
explicite ; reproductibilité APT facultative ; complétude de la wheel
réellement testée.

Il corrige également un défaut particulièrement important que les
audits précédents avaient manqué : le helper de surcharge Waitress
n'entrait pas dans le contexte Docker.

Toutefois, l'ajout du snapshot a introduit une double clé `args` dans
le Compose de production. Tant que cette erreur n'est pas corrigée, la
pile doit être considérée comme potentiellement non démarrable et le
P0 Docker reste ouvert.

**Évaluation actuelle : 8,4/10.**

Après fusion des deux blocs `args` et réussite observable du smoke
workflow, l'évaluation pourrait immédiatement revenir autour de
8,8/10.
