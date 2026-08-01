# Audit externe du dépôt (ChatGPT), quatrième passage — 1ᵉʳ août 2026

**Provenance.** Quatrième passage de l'audit statique externe (ChatGPT,
à la demande de Michaël Launay), sur le commit `c20df5c` (portes de
qualité en CI) ; passage précédent sur `885974e`. Note globale
proposée : **7,1/10**. Au fil des passages : 6,5 → 6,9 → 6,7 → 7,1 —
l'échelle de l'auditeur bouge d'un passage à l'autre (le troisième a
rebasé sa référence), la pente est ce qui compte. Le texte intégral est
reproduit en seconde partie de ce document.

**Statut.** Contre-expertisé sur pièces le jour même (clone vierge du
master, chaque constat vérifié — l'un empiriquement). Plan d'exécution
en quatre volets adopté (patchs 0071+). Les trois décisions
d'architecture du premier passage — journaux de mots de passe chiffrés
en DEBUG conservés, globales de `constants_and_globals` voulues,
Keycloak non exclusif — restent actées ; **l'audit ne les remet plus en
cause**.

## Contre-expertise

L'audit est exact sur tous ses constats vérifiables ; les trois
blocages Docker qu'il répète depuis deux passages sont réels et
confirmés à la ligne :

- **Les deux scripts exigent `setup.py`**
  (`docker/start_pyramid.sh` et `docker/start_test_pyramid.sh`, l.12),
  supprimé au profit de `pyproject.toml` par le patch d'empaquetage :
  le conteneur sort avant `pserve`.
- **`use_forwarded_proto = true` tue Waitress** : vérifié
  *empiriquement* — `waitress==3.0.2` (la version du verrou) lève
  `ValueError: Unknown adjustment 'use_forwarded_proto'` à la
  construction des `Adjustments`. L'option, héritée d'une autre pile,
  était inerte tant qu'elle vivait dans `[app:main]` ; le déplacement
  des options serveur vers `[server:main]` (correction du deuxième
  passage) l'a rendue létale. À supprimer partout — `url_scheme =
  https` couvre déjà le besoin.
- **`listen = localhost:6543`** est inatteignable depuis le conteneur
  Apache, et **`trusted_proxy = 127.0.0.1`** ne correspond pas à
  l'adresse qu'Apache présente sur le réseau compose — le limiteur de
  connexions rabattrait alors tous les visiteurs sur une seule
  fenêtre. Le healthcheck interne (`urlopen('http://localhost:6543')`)
  peut, lui, rester vert : c'est précisément pourquoi rien ne le voit.
  **Nuance** : ces deux valeurs sont les *bonnes* pour le déploiement
  nu (chapitre 13, « Déploiement sans conteneurs »), où Apache et
  Waitress partagent l'hôte. La correction n'est donc pas de changer
  `production.ini` pour tout le monde, mais de donner à la pile Docker
  sa propre configuration serveur.
- **§4, verrou commun** : l'inférence de l'auditeur est confirmée sur
  pièces — `requirements.lock` à `c20df5c` épingle `ruff`, `bandit`,
  `mypy`, `pip-audit`, `pytest`…, et `DockerfilePyramid` installe ce
  verrou (après une mise à niveau `pip setuptools wheel` *hors verrou*,
  l.52, elle aussi pointée à raison). L'image de production embarque
  donc les outils de test et de qualité. `pyramid_debugtoolbar` est par
  ailleurs bien une dépendance *runtime* du `pyproject.toml`.
- **`.env.example`** documente `MAIL_USE_TLS`/`MAIL_USE_SSL` là où le
  code lit `MAIL_TLS`/`MAIL_SSL`, et présente `LDAP_SERVER` comme une
  URL avec schéma et port alors que le code passe serveur et port
  séparément à `ldap3.Server`. Confirmé.
- Les points de sécurité rappelés (synchronisation LDAP bilatérale non
  atomique, `init.sh` transmettant encore mots de passe et données
  personnelles par `argv`, refresh token signé mais non chiffré,
  réponses Keycloak non validées champ à champ, LDAP sans TLS, cache
  `Server` aveugle à ses paramètres, rappels sur `NewRequest`) sont les
  restes connus des plans précédents — tous confirmés encore ouverts.

Deux nuances mesurées. **« 957 tests et ~70 % non vérifiés
indépendamment »** : le connecteur GitHub de l'auditeur n'a rien
retourné pour ce commit ; les chiffres sont reproductibles localement
(clone vierge, `mkdir var`, `pytest --cov`) et les workflows du commit
sont verts. **Le throttling « global » derrière le proxy** est la
déclinaison conteneurisée du point traité au premier passage pour
l'hôte nu : le mécanisme (`trusted_proxy` + fenêtres par adresse) est
en place, seule la *valeur* est fausse pour compose.

## Décisions actées (rappel)

Inchangées depuis le premier passage, et désormais intégrées par
l'auditeur lui-même :

1. **Les journaux de mots de passe chiffrés (DEBUG) sont conservés** —
   outil de diagnostic assumé, chiffré RSA-OAEP/SHA-256 vers une clé
   publique fournie par l'environnement, sous responsabilité de
   l'administrateur.
2. **Les globales de `constants_and_globals` sont un choix** ; en
   revanche le `.env` n'est lu qu'une fois (fait, quatrième train de
   correctifs).
3. **Keycloak ne deviendra pas l'unique point d'authentification** —
   le serveur de test n'y est pas relié et n'héberge qu'AlirPunkto.

## Plan d'exécution

### 0071 — P0 : rendre la pile Docker démarrable

- `pyproject.toml` remplace `setup.py` dans les deux scripts de
  démarrage ;
- suppression de `use_forwarded_proto` (partout) ;
- configuration serveur propre à la pile : écoute sur `0.0.0.0:6543`
  *dans le conteneur* (publication hôte restant sur `127.0.0.1`, ou
  retirée), adresse fixe du conteneur Apache sur le réseau compose et
  `trusted_proxy` sur cette adresse — sans toucher aux valeurs du
  déploiement nu ;
- **smoke test Compose en CI** : construction des images, `up`,
  attente des healthchecks, requête de bout en bout *à travers
  Apache*, vérification dans les journaux que `client_addr` est
  l'adresse réelle (pas celle du proxy), `down` inconditionnel. Ce
  seul job aurait détecté les trois blocages ;
- le scanner de secrets (gitleaks, épinglé par SHA) monte dans le même
  train : c'est une addition de workflow.

### 0072 — P1 : séparer l'exécution du développement

- trois verrous générés avec empreintes (`--generate-hashes`) :
  runtime, test, qualité ; la CI de tests installe le verrou de test,
  le workflow qualité le sien, Docker le verrou runtime seul ;
- `DockerfilePyramid` multiétape (constructeur avec compilateurs et
  en-têtes → image finale sans), base épinglée par digest, plus aucune
  mise à niveau hors verrou ;
- `pyramid_debugtoolbar` déplacé vers un extra de développement
  (`development.ini` le charge, l'image de production ne l'embarque
  plus).

### 0073+ — P2 : sécurité restante

- `init.sh` branche enfin `GENERATE_LDIF_*_PW` et passe les données
  personnelles par fichier temporaire `0600` (ou entrée standard) —
  plus rien par `argv` ;
- synchronisation des groupes **cohérente** : le côté groupe devient
  autoritatif et le scan quotidien lit et compare les *deux* côtés
  pour réparer une divergence, au lieu de croire `uniqueMemberOf`
  seul ;
- refresh token **chiffré** (Fernet, clé dérivée dédiée) avant dépôt
  dans le cookie signé ;
- validation des réponses Keycloak (`json()` gardé, champs et types
  requis vérifiés) ;
- TLS LDAP avec validation de certificat : décision d'exploitation à
  trancher (réseau compose interne) ; l'objet `ldap3.Tls` et le cache
  `Server` indexé par paramètres arrivent avec.

### P3 — au fil de l'eau (cliquets)

- mypy : geler le compte (124 à l'adoption), interdire la hausse,
  rendre bloquant module par module ;
- retirer l'exception `F841`, puis étendre Ruff par familles (`E`,
  `W`, `I`, `B`, `UP`) ;
- relever `--cov-fail-under` de deux points par campagne significative
  de tests ;
- déplacer les rappels des vérificateurs de `NewRequest` vers le cron
  du chapitre 09 — l'audit converge avec la documentation maison.

# Texte intégral de l'audit (quatrième passage)

**Date :** 1er août 2026
**Dépôt :** `michaellaunay/alirpunkto`
**Branche :** `master`
**Commit examiné :** `c20df5c58898f99cf4439125a812562ee0624573`
**Audit précédent :** commit `885974e756c00fad7039e92687694b76ba84c93f`

## 1. Résumé exécutif

Le dernier commit améliore significativement l'industrialisation du
projet :

* Ruff est désormais bloquant ;
* Bandit est bloquant pour les alertes moyennes et supérieures ;
* `pip-audit` est exécuté sur le verrou ;
* un seuil minimal de couverture de 68 % est appliqué ;
* les actions GitHub sont référencées par SHA ;
* les installations hors verrou ont été supprimées du workflow de
  tests ;
* plusieurs imports morts et deux défauts réels détectés par Ruff ont
  été corrigés ;
* mypy est introduit comme contrôle informatif.

Le commit annonce également 957 tests réussis et une couverture mesurée
à environ 70 %. Je n'ai toutefois pas pu confirmer ces résultats depuis
GitHub Actions : le connecteur n'a retourné ni exécution ni statut de
vérification pour ce commit. Les résultats sont donc documentés dans le
commit, mais pas indépendamment validés ici.

La principale faiblesse reste inchangée : **la pile Docker documentée
ne peut toujours pas démarrer correctement**. Aucun fichier Docker ni
`production.ini` n'a été modifié dans ce commit.

Les trois blocages critiques restent donc présents :

1. les scripts recherchent encore `setup.py` ;
2. `production.ini` contient une option Waitress inconnue ;
3. Waitress écoute sur la boucle locale du conteneur Pyramid.

## 2. Évaluation actualisée

| Domaine                           | Note précédente | Nouvelle note |
| --------------------------------- | --------------: | ------------: |
| Architecture applicative          |             7,2 |           7,2 |
| Qualité du code                   |             6,8 |           7,3 |
| Tests                             |             7,3 |           7,7 |
| CI et contrôles automatiques      |             5,8 |           7,5 |
| Documentation                     |             7,3 |           7,3 |
| Dépendances et reproductibilité   |             7,1 |           7,5 |
| Sécurité applicative              |             7,3 |           7,6 |
| Sécurité et fonctionnement Docker |             4,5 |           4,5 |
| Exploitation et observabilité     |             6,0 |           6,1 |

**Note globale actualisée : 7,1/10**, contre 6,7/10 précédemment.

Le dépôt franchit le seuil d'un projet correctement contrôlé au niveau
applicatif et CI, mais reste pénalisé par l'absence de validation du
déploiement réel.

---

# 3. Nouveaux constats résolus

## 3.1 Ruff bloquant — résolu

Un nouveau workflow `quality` exécute :

```yaml
ruff check alirpunkto tests tools
```

Le contrôle est bloquant. La configuration sélectionne actuellement les
erreurs de la famille Pyflakes, avec `F841` temporairement ignoré.

Le nettoyage a notamment supprimé :

* les imports dupliqués de `Configurator` ;
* l'import dupliqué de `get_localizer` ;
* de nombreux imports inutilisés ;
* un import `requests.request` qui masquait un paramètre de vue ;
* une erreur de portée sur la variable `DOMAINE` dans un outil.

Le nettoyage des imports de `__init__.py`, précédemment signalé, est
donc résolu.

**Statut : résolu, avec une règle Ruff encore volontairement limitée.**

L'étape suivante pourra être d'activer progressivement les familles
`E`, `W`, `I`, `B`, `UP` et de retirer l'exception `F841`.

---

## 3.2 Bandit bloquant — résolu

Le workflow exécute maintenant :

```bash
bandit -r alirpunkto tools -ll -q
```

Les alertes moyennes et élevées sont donc bloquantes.

Les utilisations de SHA-1 servant à produire le format LDAP `{SSHA}`
sont explicitement documentées avec `# nosec B324`. Cette exception est
cohérente avec le besoin d'interopérabilité OpenLDAP : il ne s'agit pas
d'utiliser SHA-1 comme mécanisme général de sécurité applicative, mais
de produire un format attendu par l'annuaire.

**Statut : résolu.**

---

## 3.3 Audit des dépendances — résolu avec exception documentée

Le nouveau workflow exécute :

```bash
pip-audit -r requirements.lock --no-deps \
    --ignore-vuln PYSEC-2026-3447
```

Le contrôle est bloquant, à l'exception explicite de l'identifiant
`PYSEC-2026-3447` concernant `setuptools`. Le motif de l'exception est
documenté directement dans le workflow.

La borne de `cryptography` a également été relevée et le verrou
régénéré.

**Statut : résolu avec un risque accepté temporaire.**

L'exception `setuptools` doit rester visible et être supprimée dès que
la chaîne de dépendances permet une version corrigée.

---

## 3.4 Installations CI hors verrou — résolu

Le workflow de tests ne lance plus :

```bash
pip install --upgrade pip setuptools wheel
pip install pytest
```

Il installe le verrou, puis l'application avec `--no-deps`.

`pip`, `setuptools` et `wheel` sont maintenant inclus dans le verrou
grâce à la génération avec `--allow-unsafe`.

**Statut : résolu pour GitHub Actions.**

Ce point reste toutefois ouvert dans le Dockerfile de production, qui
continue de mettre à niveau les outils de construction avant
d'installer le verrou. Le dernier commit ne modifie pas ce fichier.

---

## 3.5 Actions GitHub fixées par SHA — résolu

Les références mobiles :

```yaml
actions/checkout@v4
actions/setup-python@v5
actions/upload-artifact@v4
```

ont été remplacées par des SHA de 40 caractères. La version lisible
reste indiquée en commentaire.

**Statut : résolu.**

---

## 3.6 Seuil de couverture — résolu

Le workflow de tests exécute maintenant :

```bash
pytest \
    --cov=alirpunkto \
    --cov-fail-under=68
```

Le seuil de 68 % est inférieur à la couverture annoncée de 70 %, ce qui
constitue un bon mécanisme de progression graduelle : la couverture ne
peut plus diminuer librement.

**Statut : résolu.**

Le seuil devra être relevé progressivement, par exemple de deux points
à chaque campagne significative de tests.

---

## 3.7 Typage statique — engagé, non bloquant

Mypy est désormais lancé sur `alirpunkto`, mais le job utilise :

```yaml
continue-on-error: true
```

Le commit indique 124 erreurs lors de l'introduction du contrôle.

**Statut : amélioration engagée, pas encore un garde-fou.**

Cette approche est raisonnable pour adopter mypy sans bloquer
immédiatement le projet. Il faudrait maintenant :

* enregistrer le nombre d'erreurs courant ;
* empêcher son augmentation ;
* corriger progressivement les modules ;
* rendre le job bloquant lorsque la dette devient maîtrisable.

---

# 4. Nouveau point d'attention : verrou commun à la production et à la qualité

Le verrou a été régénéré avec les extras :

* `testing` ;
* `quality`.

Il contient donc désormais non seulement les dépendances applicatives,
mais également :

* pytest ;
* pytest-cov ;
* Ruff ;
* Bandit ;
* pip-audit ;
* mypy ;
* leurs dépendances transitives.

Le Dockerfile Pyramid installe toujours ce même `requirements.lock`
dans l'image de production.

Par conséquent, l'image de production reçoit maintenant tous les outils
de tests et de qualité. Il s'agit d'une inférence fondée sur la
régénération annoncée du verrou avec les extras de qualité et sur
l'installation inchangée de ce verrou par Docker.

### Conséquences

* image plus volumineuse ;
* surface d'attaque accrue ;
* dépendances non nécessaires au runtime ;
* audit de vulnérabilités plus bruyant ;
* durée de construction plus longue.

### Correction recommandée

Créer trois verrous :

```text
requirements-runtime.lock
requirements-test.lock
requirements-quality.lock
```

L'image de production ne doit installer que le verrou runtime.

**Sévérité : moyenne à élevée.**

---

# 5. Blocages Docker toujours critiques

## 5.1 Les scripts exigent toujours `setup.py`

Le script de production contient encore :

```bash
if [ ! -f "${APP_DIR}/setup.py" ] ||
   [ ! -d "${APP_DIR}/alirpunkto" ]; then
    exit 1
fi
```

Le même contrôle existe dans `start_test_pyramid.sh`.

Or `setup.py` a été supprimé et remplacé par `pyproject.toml`.

### Conséquence

Le conteneur Pyramid s'arrête avant d'exécuter `pserve`.

### Correction

```bash
if [ ! -f "${APP_DIR}/pyproject.toml" ] ||
   [ ! -d "${APP_DIR}/alirpunkto" ]; then
```

**Statut : critique, ouvert.**

---

## 5.2 Option Waitress inexistante

`production.ini` contient encore :

```ini
use_forwarded_proto = true
```

Cette option ne fait pas partie des paramètres de Waitress 3.0.2.
Waitress refuse les options inconnues avec une `ValueError`.

### Correction

Supprimer cette ligne.

**Statut : critique, ouvert.**

---

## 5.3 Waitress écoute sur `localhost`

La configuration contient encore :

```ini
listen = localhost:6543
```

Apache se trouve dans un autre conteneur. Il ne peut donc pas atteindre
la boucle locale du conteneur Pyramid.

### Correction

Pour la pile Docker :

```ini
listen = 0.0.0.0:6543
```

Le port n'a pas besoin d'être exposé publiquement sur l'hôte.

**Statut : critique, ouvert.**

---

## 5.4 Proxy Apache non reconnu par Waitress

La configuration utilise toujours :

```ini
trusted_proxy = 127.0.0.1
```

Apache communique avec Pyramid par le réseau Docker. Son adresse source
n'est donc pas `127.0.0.1`.

### Conséquence

Le throttling peut considérer tous les utilisateurs comme provenant de
l'adresse du proxy Apache.

**Statut : élevé, ouvert.**

---

# 6. Limites de la nouvelle CI

La nouvelle CI contrôle correctement le code Python et les dépendances,
mais elle ne valide toujours pas :

* la construction des images Docker ;
* le démarrage de Compose ;
* la validité effective de `production.ini` pour Waitress ;
* la communication Apache → Pyramid ;
* la remontée de l'adresse IP réelle ;
* les healthchecks de la pile ;
* les migrations ou initialisations LDAP ;
* la détection de secrets.

Le commit reconnaît explicitement que le build Docker, le smoke test
Compose, le test de bout en bout via Apache et le secret scanning
restent hors périmètre.

### Test prioritaire à ajouter

Un job CI doit :

1. construire les images ;
2. générer une configuration de test ;
3. exécuter `docker compose up -d`;
4. attendre les healthchecks ;
5. interroger l'application à travers Apache ;
6. vérifier les journaux ;
7. arrêter la pile même en cas d'échec.

Ce test aurait immédiatement détecté les trois blocages critiques.

---

# 7. Constats antérieurs toujours partiellement ouverts

## 7.1 Synchronisation LDAP bidirectionnelle

Les échecs de `conn.modify()` sont maintenant contrôlés et journalisés,
mais les deux côtés de la relation LDAP sont toujours modifiés
indépendamment.

Une divergence entre :

* `group.uniqueMember` ;
* `member.uniqueMemberOf`;

reste donc possible.

**Statut : partiellement résolu.**

---

## 7.2 Mots de passe du générateur LDIF

`generate_ldif.py` sait lire les mots de passe depuis des variables
d'environnement, mais `init.sh` transmet encore les valeurs dans les
arguments positionnels.

Lorsque `slappasswd` manque, le mot de passe clair peut donc encore
apparaître temporairement dans la ligne de commande du processus.

**Statut : partiellement résolu.**

---

## 7.3 Refresh token Keycloak

Le refresh token reste stocké directement dans une session cookie
signée, mais non chiffrée.

**Statut : ouvert.**

---

## 7.4 Validation des réponses Keycloak

Les appels ont des délais maximaux et gèrent les erreurs réseau, mais :

* `response.json()` peut échouer ;
* les champs obligatoires ne sont pas vérifiés ;
* les types ne sont pas validés.

**Statut : ouvert.**

---

## 7.5 LDAP sans TLS validé

La configuration utilise encore le port 389 et `LDAP_USE_SSL=false`. La
fabrique ne définit pas d'objet `Tls` avec validation de certificat.

**Statut : ouvert.**

---

## 7.6 Cache du serveur LDAP

Le premier objet LDAP `Server` construit reste mis en cache sans tenir
compte des paramètres des appels ultérieurs.

**Statut : ouvert.**

---

## 7.7 Rappels dans le cycle HTTP

Les rappels aux vérificateurs restent déclenchés depuis l'événement
`NewRequest`.

**Statut : ouvert.**

---

## 7.8 `.env.example`

Le fichier documente toujours `MAIL_USE_TLS` et `MAIL_USE_SSL`, tandis
que le code attend `MAIL_TLS` et `MAIL_SSL`. Il décrit également
`LDAP_SERVER` comme une URL complète alors que le port est fourni
séparément.

**Statut : ouvert.**

---

# 8. Dépendances et reproductibilité

## Points désormais satisfaisants

* dépendances applicatives bornées ;
* verrou exact ;
* installation CI depuis le verrou ;
* outils de CI inclus dans le verrou ;
* audit automatisé des vulnérabilités ;
* actions GitHub fixées par SHA ;
* mise à jour de `cryptography`.

## Points encore ouverts

* absence de hashes dans le verrou ;
* verrou unique pour runtime, tests et qualité ;
* mise à niveau hors verrou dans le Dockerfile ;
* image Ubuntu non fixée par digest ;
* image Pyramid toujours monoétape ;
* compilateurs et en-têtes de développement conservés dans l'image
  finale ;
* `pyramid_debugtoolbar` reste une dépendance runtime.

---

# 9. Plan d'action révisé

## P0 — Rendre la pile Docker démarrable

1. Remplacer `setup.py` par `pyproject.toml` dans les scripts.
2. Supprimer `use_forwarded_proto`.
3. Faire écouter Waitress sur une interface accessible par Apache.
4. Corriger `trusted_proxy`.
5. Ajouter un smoke test Compose.

## P1 — Séparer runtime et développement

1. Créer un verrou runtime.
2. Créer un verrou de tests.
3. Créer un verrou qualité.
4. Construire une image multiétape.
5. Retirer compilateurs, pytest, Ruff, Bandit, mypy et pip-audit de
   l'image finale.
6. Ajouter des hashes aux verrous.

## P2 — Sécurité restante

1. Activer TLS LDAP avec validation de certificat.
2. Chiffrer le refresh token.
3. Valider les réponses JSON Keycloak.
4. Finaliser le transport hors `argv` des données LDIF.
5. Rendre la synchronisation des groupes LDAP cohérente.
6. Ajouter un secret scanner.

## P3 — Dette de qualité

1. Réduire les 124 erreurs mypy.
2. Rendre mypy bloquant par module.
3. Retirer progressivement l'exception Ruff `F841`.
4. Étendre Ruff au style, aux imports et aux modernisations Python.
5. Relever progressivement le seuil de couverture.

---

# 10. Conclusion

Le commit `c20df5c…` est une amélioration importante et correctement
orientée.

Le dépôt dispose maintenant de véritables garde-fous contre :

* les imports et références invalides ;
* plusieurs erreurs de programmation détectables statiquement ;
* les faiblesses de sécurité Python de sévérité moyenne ou élevée ;
* les dépendances vulnérables non explicitement acceptées ;
* les baisses de couverture ;
* les modifications silencieuses d'actions GitHub.

La qualité du projet n'est désormais plus seulement déclarative : elle
est partiellement imposée par la CI.

Cependant, la CI contrôle surtout le code Python isolé. Elle ne
garantit toujours pas que le produit livré démarre. La pile Docker
reste bloquée par trois erreurs simples que seul un test d'intégration
aurait détectées.

**Évaluation actuelle : 7,1/10.**

Après correction des points Docker P0 et ajout du smoke test, une
évaluation comprise entre **7,8 et 8,1/10** serait justifiée sans
remettre en cause les choix d'architecture actés.
