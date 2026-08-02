# Audit externe du dépôt (ChatGPT), sixième passage — 1ᵉʳ août 2026

**Provenance.** Sixième passage de l'audit statique externe (ChatGPT, à
la demande de Michaël Launay), sur le commit `e80f39e` (verrous séparés
et image multiétape) ; passage précédent (le cinquième, noté 7,8 sur
`21ebee1`, texte non transmis). Note globale proposée : **8,2/10**. Au
fil des passages : 6,5 → 6,9 → 6,7 → 7,1 → 7,8 → 8,2. Le texte intégral
est reproduit en seconde partie de ce document.

**Statut.** Contre-expertisé sur pièces le jour même. P0 (démarrage
Docker) et P1 (chaîne d'approvisionnement) déclarés fermés par
l'auditeur — qui précise honnêtement que le connecteur GitHub ne lui
remonte aucune exécution Actions pour ce SHA : les chiffres de tests
sont ceux des messages de commit, non confirmés indépendamment. Les
trois décisions d'architecture restent actées et non remises en cause.
Réponse apportée : patchs 0073 (P2, items 1 à 4) et 0074 (items 5 et
6), évalués par le huitième passage
(`20260802_audit_externe_chatgpt_alirpunkto_8e_passage.md`).

## Contre-expertise

Les constats applicatifs du §12 ont tous été vérifiés sur pièces avant
correction :

- **§12.1, TLS LDAP** : confirmé *sur les sources de ldap3 2.9.1* —
  sans objet `Tls`, la valeur par défaut est `ssl.CERT_NONE` : aucun
  certificat n'est validé. Vérifié aussi : quand un objet `Tls` exige
  `CERT_REQUIRED`, ldap3 charge le magasin système en l'absence de
  fichier CA (`load_default_certs`) et vérifie lui-même le nom d'hôte.
- **§12.2, cache serveur** : confirmé — `_server` était un singleton de
  module retourné quels que soient les paramètres ; le premier appel
  imposait hôte, port et mode SSL aux suivants.
- **§12.5, jeton de rafraîchissement** : confirmé — écrit en clair par
  l'unique point d'écriture `store_sso_tokens`, dans un cookie signé
  (intégrité) mais non chiffré (confidentialité). La correction a
  révélé une contrainte que l'audit ne pouvait pas voir : chiffrer sans
  compresser aurait fait ré-exploser le budget cookie de 4093 octets
  (l'incident de terrain du 2026-07-08) — d'où le scellement
  « compression puis chiffrement », documenté dans le code.
- **§12.6, réponses Keycloak** : confirmé — `response.json()` pouvait
  lever, aucun champ ni type n'était contrôlé, les durées d'expiration
  n'étaient pas bornées.
- **§12.4** : les deux précisions de l'auditeur sont exactes — le
  commentaire « NUL-separated env vars » ne correspondait pas au code
  (un tableau Bash développé en arguments positionnels), et le repli de
  `hash_password` renvoyait le mot de passe en clair quand `slappasswd`
  manquait.
- **Réserves image (§11)** : toutes fondées ; traitées par le train de
  finition d'image (0075), qui a de surcroît débusqué que « tout en
  wheels » était une illusion du cache pip (trois paquets du verrou
  sont sdist-only, purs Python) et réparé une casse latente de premier
  démarrage (le helper d'overrides exclu de l'image par
  `.dockerignore`).

## Décisions actées (rappel)

Inchangées depuis le premier passage : journaux de mots de passe
chiffrés en DEBUG conservés ; globales de `constants_and_globals`
voulues ; Keycloak jamais point d'authentification unique. L'activation
de LDAPS dans la pile compose reste une décision d'exploitation du
client — le mécanisme validant est prêt (0073), le défaut réseau
interne inchangé.

## Plan d'exécution adopté

- **0073** — P2 items 1 à 4 : TLS LDAP validant (`Tls` +
  `LDAP_CA_CERT_FILE` optionnel), cache serveur indexé par paramètres,
  scellement du jeton de rafraîchissement (zlib puis Fernet), validation
  stricte des réponses Keycloak (champs, types, borne 90 jours, journal
  sans corps).
- **0074** — P2 items 5 et 6 : transport LDIF hors `argv` (généralisation
  des slots d'environnement), cohérence des groupes (lecture des deux
  côtés, convergence par côté, découverte du scan par les deux côtés).
- **Finition d'image** (réserves §11) : wheel applicative,
  `--only-binary` avec exceptions nommées, contexte réduit, snapshot APT
  opt-in — livrée en 0075.

# Texte intégral de l'audit (sixième passage)

# Audit actualisé du dépôt AlirPunkto — sixième passage

**Date :** 1er août 2026
**Dépôt :** `michaellaunay/alirpunkto`
**Branche :** `master`
**Commit examiné :** `e80f39e912e239cc267dda8489bc68cbc57f37ac`
**Audit précédent :** commit `21ebee1ea943bbef0d539e881eb4f88d333dfd0a`

## 1. Résumé exécutif

Le dernier commit ferme l'essentiel du P1 relatif à la chaîne de
construction et à l'image de production.

Les améliorations principales sont :

* séparation des dépendances runtime, tests et qualité dans trois verrous ;
* ajout de hashes SHA-256 sur toutes les dépendances verrouillées ;
* utilisation de `--require-hashes` lors des installations ;
* suppression de pytest, Ruff, Bandit, mypy et `pip-audit` de l'image de production ;
* déplacement de `pyramid_debugtoolbar` dans un extra de développement ;
* passage de l'image Pyramid à une construction multiétape ;
* suppression de la mise à niveau non verrouillée de pip, setuptools et wheel ;
* retrait des compilateurs et en-têtes de développement de l'image finale ;
* épinglage par digest des quatre images Ubuntu ;
* audit des trois verrous par `pip-audit` ;
* ajout de tests de non-régression sur l'ensemble de cette chaîne.

Le commit annonce :

* 974 tests réussis ;
* une couverture de 71,61 % ;
* une exécution dans un environnement construit uniquement depuis le verrou de tests.

Ces résultats sont documentés dans le message de commit, mais le
connecteur GitHub ne remonte actuellement ni exécution Actions ni statut
combiné pour ce SHA. Ils ne sont donc pas indépendamment confirmés dans
cet audit.

La chaîne Python et Docker atteint désormais un bon niveau de
reproductibilité. Elle n'est toutefois pas encore strictement
reproductible bit à bit, principalement parce que les paquets Ubuntu
installés avec `apt-get` ne sont ni versionnés ni servis depuis un dépôt
figé.

## 2. Évaluation actualisée

| Domaine                           | Note précédente | Nouvelle note |
| --------------------------------- | --------------: | ------------: |
| Architecture applicative          |             7,4 |           7,5 |
| Qualité du code                   |             7,5 |           7,6 |
| Tests                             |             8,4 |           8,7 |
| CI et contrôles automatiques      |             8,8 |           9,0 |
| Documentation                     |             7,9 |           8,0 |
| Dépendances et reproductibilité   |             7,5 |           9,0 |
| Sécurité applicative              |             7,7 |           7,7 |
| Sécurité et fonctionnement Docker |             8,3 |           9,0 |
| Exploitation et observabilité     |             7,0 |           7,2 |

**Note globale actualisée : 8,2/10**, contre 7,8/10 précédemment.

Le projet dispose maintenant d'une chaîne de construction solide, testée
structurellement et protégée contre de nombreuses dérives de dépendances.

---

# 3. Séparation des verrous — résolu

Trois fichiers distincts existent désormais :

```text
requirements.lock
requirements-test.lock
requirements-quality.lock
```

Le premier contient uniquement les dépendances nécessaires à
l'exécution. Les deux autres ajoutent respectivement les dépendances de
tests et de qualité. Cette structure est également documentée dans
`pyproject.toml`.

Les en-têtes des trois fichiers montrent qu'ils sont générés avec :

```text
--generate-hashes
--allow-unsafe
--strip-extras
```

## Conséquences positives

* les outils de développement ne sont plus livrés en production ;
* les versions runtime restent identiques dans les trois voies ;
* une dépendance modifiée sur l'index sans correspondre au hash attendu est refusée ;
* les dépendances de tests et de qualité peuvent évoluer sans gonfler l'image de production.

**Statut : résolu.**

---

# 4. Installation avec vérification des hashes — résolu

Le Dockerfile installe maintenant le verrou runtime avec :

```dockerfile
pip install --require-hashes -r requirements.lock
```

Le workflow de tests utilise :

```bash
pip install --require-hashes -r requirements-test.lock
```

Les jobs Ruff, Bandit, mypy et `pip-audit` utilisent le verrou qualité
avec le même contrôle.

Les scripts de démarrage installent également le verrou de tests avec
`--require-hashes` lorsque `INSTALL_EXTRAS_TESTING` est explicitement
activé.

**Statut : résolu.**

---

# 5. Audit des trois verrous — résolu

Le workflow qualité soumet les trois fichiers à `pip-audit` :

```bash
pip-audit \
  --no-deps \
  --ignore-vuln PYSEC-2026-3447 \
  -r requirements.lock \
  -r requirements-test.lock \
  -r requirements-quality.lock
```

L'utilisation répétée de `-r` est bien prise en charge officiellement
par `pip-audit`. Sa documentation indique également que
`--require-hashes` est préférable lorsque les fichiers sont entièrement
hashés. Dans ce dépôt, la vérification des hashes est déjà effectuée
lors de l'installation de chaque voie ; l'audit utilise ensuite
`--no-deps` pour éviter une nouvelle résolution.

L'exception `PYSEC-2026-3447` reste explicitement documentée.

**Statut : résolu avec un risque accepté.**

L'exception devra être retirée dès que la chaîne de dépendances
permettra une version non concernée.

---

# 6. Outils de tests absents du runtime — résolu

Le nouveau test `test_the_runtime_lock_ships_no_tooling` interdit dans
le verrou runtime :

* pytest ;
* pytest-cov ;
* WebTest ;
* Ruff ;
* Bandit ;
* mypy ;
* `pip-audit` ;
* `pyramid_debugtoolbar`.

`pyramid_debugtoolbar` se trouve maintenant uniquement dans l'extra
`dev`, puisque seule la configuration de développement l'utilise.

**Statut : résolu.**

---

# 7. Image Pyramid multiétape — résolu

Le Dockerfile comporte désormais deux étapes.

## Étape de construction

Elle contient :

* les compilateurs ;
* les en-têtes Python ;
* les bibliothèques de développement LDAP, SSL, XML et images ;
* le virtualenv ;
* les dépendances Python.

## Étape d'exécution

Elle ne conserve que :

* Python ;
* les certificats d'autorité ;
* le virtualenv construit ;
* les sources applicatives ;
* le script de démarrage.

Les compilateurs et paquets `*-dev` ne sont plus présents dans l'image
finale.

Le Dockerfile copie également le verrou avant les sources, ce qui permet
de réutiliser la couche des dépendances lorsqu'une modification ne
concerne que le code.

**Statut : résolu.**

---

# 8. Installation hors verrou supprimée — résolu

L'ancien Dockerfile exécutait :

```dockerfile
pip install --upgrade pip setuptools wheel
```

Cette étape a disparu.

Le virtualenv utilise le pip fourni lors de sa création et installe les
versions définies dans le verrou. L'installation du projet utilise
`--no-build-isolation`, évitant le téléchargement automatique d'un
environnement de construction non verrouillé.

**Statut : résolu.**

---

# 9. Images de base épinglées par digest — résolu

Les images Pyramid, Apache, LDAP et Postfix utilisent maintenant une
référence de la forme :

```dockerfile
FROM ubuntu:24.04@sha256:...
```

Le Dockerfile Apache le confirme directement.

Un test parcourt tous les `Dockerfile*` et exige un digest SHA-256 sur
chaque instruction `FROM`.

Cela empêche une modification silencieuse de l'image associée au tag
`ubuntu:24.04`.

**Statut : résolu.**

---

# 10. Tests de chaîne d'approvisionnement — résolu

Le nouveau fichier `tests/test_supply_chain.py` contrôle :

* la présence de trois verrous hashés ;
* l'absence d'outils de tests dans le runtime ;
* l'identité des versions runtime dans les trois verrous ;
* le placement de la debug toolbar dans l'extra `dev` ;
* la construction multiétape ;
* l'absence de mise à niveau de pip hors verrou ;
* l'épinglage de toutes les images de base ;
* l'utilisation du bon verrou par chaque workflow ;
* l'utilisation du verrou de tests par les scripts de démarrage.

Ces tests complètent correctement le smoke test Docker ajouté au passage
précédent.

**Statut : résolu.**

---

# 11. Réserves restantes sur l'image

## 11.1 Installation éditable en production

L'application reste installée avec :

```dockerfile
pip install --no-build-isolation --no-deps -e .
```

Cela fonctionne parce que les sources sont recopiées dans le même chemin
dans l'image finale. Cependant, une installation éditable n'est pas
indispensable dans une image immuable.

Une installation classique serait plus simple à raisonner :

```bash
pip install --no-build-isolation --no-deps .
```

ou via une wheel applicative construite lors de la première étape.

**Statut : ouvert, sévérité faible.**

---

## 11.2 Hypothèse que toutes les dépendances sont disponibles en wheels

Le Dockerfile indique que toutes les dépendances verrouillées actuelles
disposent d'une wheel. Cependant, l'étape de construction conserve
volontairement les compilateurs au cas où un futur verrou introduirait
une archive source.

Cela crée un risque futur :

1. une dépendance est compilée contre une bibliothèque système dans l'étape builder ;
2. le virtualenv est copié ;
3. la bibliothèque partagée correspondante n'existe pas dans l'image finale ;
4. l'import échoue seulement à l'exécution.

### Recommandation

Imposer dans l'image :

```bash
pip install --only-binary=:all: --require-hashes \
  -r requirements.lock
```

Ainsi, l'absence de wheel provoque un échec de construction explicite.

Autre possibilité : lister précisément les bibliothèques runtime
nécessaires dans la deuxième étape.

**Statut : ouvert, sévérité moyenne préventive.**

---

## 11.3 Les paquets APT ne sont pas figés

Les images de base sont immuables grâce au digest, mais les commandes
suivantes restent temporelles :

```dockerfile
apt-get update
apt-get install ...
```

Deux constructions réalisées à des dates différentes peuvent donc
obtenir des révisions différentes des paquets Ubuntu, même avec la même
image de base.

### Recommandation

Pour une reproductibilité stricte :

* utiliser un snapshot Ubuntu daté ;
* ou fixer les versions APT ;
* ou construire et publier des images internes signées, puis déployer uniquement leur digest.

**Statut : ouvert, sévérité moyenne pour la reproductibilité stricte.**

---

## 11.4 Quelques artefacts non runtime restent copiés

Le `.dockerignore` exclut déjà :

* les tests ;
* les outils ;
* la documentation ;
* les environnements virtuels ;
* les fichiers secrets ;
* les données runtime.

Toutefois, l'image finale peut encore recevoir avec `COPY .` :

* `.github/` ;
* `requirements-test.lock` ;
* `requirements-quality.lock` ;
* certains fichiers de configuration de développement.

Ce point n'a pas d'impact majeur sur la sécurité, mais une liste de
copie plus explicite produirait une image encore plus propre.

**Statut : ouvert, sévérité faible.**

---

# 12. Constats applicatifs toujours ouverts

## 12.1 TLS LDAP

La fabrique LDAP utilise toujours `Server(..., use_ssl=...)` sans objet
`Tls` imposant :

* la validation du certificat ;
* une autorité de confiance ;
* un nom de serveur attendu.

Le cache `_server` reste également unique, quel que soit le serveur, le
port ou le mode TLS demandé.

**Statut : ouvert.**

---

## 12.2 Cache du serveur LDAP

Dès que `_server` est défini, `get_ldap_server()` le retourne sans
comparer les paramètres de l'appel.

Un premier appel peut donc imposer son serveur et son mode SSL aux
suivants.

**Statut : ouvert.**

---

## 12.3 Cohérence bidirectionnelle des groupes

Les échecs LDAP sont journalisés, mais les modifications de :

* `group.uniqueMember` ;
* `member.uniqueMemberOf`;

restent indépendantes.

Une moitié de la relation peut être appliquée sans l'autre.

**Statut : partiellement résolu.**

---

## 12.4 Données LDIF encore transmises dans `argv`

Le générateur sait lire les mots de passe depuis des variables
d'environnement, mais `docker/init.sh` continue de construire un tableau
d'arguments contenant :

* les hashes ou mots de passe ;
* les adresses électroniques ;
* les noms ;
* les dates de naissance ;
* les descriptions.

Le commentaire affirmant qu'il s'agit de variables d'environnement
séparées par NUL ne correspond pas au code : il s'agit d'un tableau Bash
développé comme arguments positionnels.

Le chemin de repli de `hash_password` peut encore transmettre le mot de
passe clair lorsque `slappasswd` manque.

**Statut : partiellement résolu.**

---

## 12.5 Refresh token Keycloak

Le refresh token reste stocké directement dans la session cookie signée.

La signature protège l'intégrité, mais pas la confidentialité.

**Statut : ouvert.**

---

## 12.6 Validation des réponses Keycloak

Les appels ont désormais des délais maximaux et gèrent les erreurs
réseau, mais :

* `response.json()` peut échouer ;
* les champs requis peuvent manquer ;
* les types ne sont pas validés ;
* les valeurs d'expiration ne sont pas contrôlées.

**Statut : ouvert.**

---

## 12.7 Tâche de rappel dans le cycle HTTP

Le rappel des vérificateurs reste exécuté depuis l'événement
`NewRequest`.

Cette architecture ne garantit pas l'exécution sans trafic et devient
fragile avec plusieurs processus.

**Statut : ouvert.**

---

## 12.8 `.env.example` incohérent

Le fichier utilise toujours :

```text
MAIL_USE_TLS
MAIL_USE_SSL
```

alors que l'application lit :

```text
MAIL_TLS
MAIL_SSL
```

Il présente également `LDAP_SERVER` comme une URL complète alors que le
port est configuré séparément.

**Statut : ouvert.**

---

# 13. Priorités révisées

## P0 — fermé

* démarrage Docker ;
* configuration Waitress ;
* proxy Apache ;
* smoke test de bout en bout ;
* scan de secrets.

## P1 — fermé dans son objectif principal

* séparation des verrous ;
* hashes ;
* runtime sans outils de tests ;
* image multiétape ;
* suppression des mises à jour pip hors verrou ;
* images de base épinglées.

## P2 — sécurité applicative

1. Activer TLS LDAP avec validation du certificat.
2. Corriger le cache LDAP.
3. Chiffrer le refresh token Keycloak.
4. Valider les réponses Keycloak.
5. Finaliser le transport LDIF hors `argv`.
6. Garantir la cohérence des relations de groupes LDAP.

## P3 — finition de l'image

1. Construire une wheel de l'application plutôt qu'une installation éditable.
2. Imposer `--only-binary=:all:`.
3. Figer ou snapshotter les paquets APT.
4. Réduire encore le contexte copié dans l'image.
5. Publier et déployer les images par digest.

## P4 — exploitation et dette

1. Sortir les rappels du cycle HTTP.
2. Corriger `.env.example`.
3. Réduire les erreurs mypy.
4. Étendre progressivement Ruff.
5. Augmenter le seuil de couverture.
6. Tester le renouvellement Certbot.
7. Ajouter une CSP testée.

---

# 14. Conclusion

Le commit `e80f39e…` améliore fortement la qualité de livraison.

La chaîne Python est maintenant :

* séparée par usage ;
* bornée ;
* verrouillée ;
* hashée ;
* auditée ;
* testée ;
* dépourvue d'outils de développement dans le runtime.

La chaîne Docker est maintenant :

* multiétape ;
* basée sur des images épinglées ;
* sans compilateurs dans l'image finale ;
* testée par un smoke test réel ;
* protégée contre les régressions de configuration.

Les principaux problèmes restants ne concernent plus le démarrage, le
packaging ou la CI. Ils se concentrent désormais sur :

* LDAP ;
* Keycloak ;
* la cohérence transactionnelle ;
* le transport des secrets ;
* les tâches périodiques ;
* la reproductibilité stricte des paquets système.

**Évaluation actuelle : 8,2/10.**

Une note proche de **8,7/10** deviendrait justifiée après sécurisation
LDAP, chiffrement du refresh token, validation stricte de Keycloak et
correction complète du transport LDIF.
