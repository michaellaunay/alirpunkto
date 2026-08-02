# Audit externe du dépôt (ChatGPT), cinquième passage — 1ᵉʳ août 2026

**Provenance.** Cinquième passage de l'audit statique externe (ChatGPT,
à la demande de Michaël Launay), sur le commit `21ebee1` (train Docker
P0) ; passage précédent sur `c20df5c`. Note globale proposée :
**7,8/10**. Au fil des passages : 6,5 → 6,9 → 6,7 → 7,1 → 7,8. Texte
transmis a posteriori (le 2026-08-02, avec les 7ᵉ, 9ᵉ et 11ᵉ) et versé
pour l'archive : les constats décrits ici ont depuis été traités par
les trains 0072 à 0078 — ce document décrit un état historique du
dépôt, pas sa situation actuelle.

**Statut (rétrospectif).** L'audit valide le train P0 par inspection :
les quatre blocages Docker sont déclarés résolus, le smoke test jugé
« correctement conçu » — la mécanique de preuve du `client_addr` (danse
CSRF, onze échecs, adresse extraite du journal de throttling) est
décrite exactement comme construite. Deux précisions de valeur
durable : §8.2 relève très justement que le smoke *dogfoodait* les
slots d'environnement mais que `docker/init.sh`, lui, n'était pas
encore migré (fait en 0074 puis refait en 0076) ; §7.5 note que le
port Waitress publié sur la boucle locale de l'hôte
(`127.0.0.1:6543`) est un contournement possible d'Apache pour un
processus local — risque faible, **décision d'exploitation** toujours
ouverte. Le plan P1 image qu'il dresse (trois verrous, multiétape,
suppression de l'upgrade hors verrou, non-editable, digests) est
exactement celui exécuté par 0072 puis 0075.

## Suites données

0072 (verrous/image), 0073 (LDAP/Keycloak), 0074+0076 (LDIF/groupes),
0075 (finition image), 0078 (appelants) — chroniques dans les
versements des passages suivants.

# Texte intégral de l'audit (cinquième passage)

# Audit actualisé du dépôt AlirPunkto — cinquième passage

**Date :** 1er août 2026
**Dépôt :** `michaellaunay/alirpunkto`
**Branche :** `master`
**Commit examiné :** `21ebee1ea943bbef0d539e881eb4f88d333dfd0a`
**Audit précédent :** commit `c20df5c58898f99cf4439125a812562ee0624573`

## 1. Résumé exécutif

Le dernier train de modifications corrige les principaux blocages de
déploiement signalés lors des passages précédents.

Les quatre constats Docker prioritaires sont désormais traités :

* les scripts vérifient `pyproject.toml` au lieu du fichier `setup.py` supprimé ;
* l'option Waitress invalide `use_forwarded_proto` a disparu ;
* Waitress écoute sur `0.0.0.0:6543` à l'intérieur de Compose ;
* Waitress fait confiance à l'adresse réelle du conteneur Apache et non à `127.0.0.1`.

La distinction entre les deux modes de déploiement est bien conçue :

* `production.ini` conserve les valeurs adaptées à un déploiement direct sur l'hôte, avec Apache local ;
* le conteneur génère une copie `production.generated.ini` contenant uniquement les deux substitutions nécessaires à Docker.

Un véritable smoke test GitHub Actions a également été ajouté. Il :

1. construit les images réelles ;
2. initialise une pile jetable ;
3. démarre Compose avec les healthchecks ;
4. passe par le vhost HTTPS Apache ;
5. vérifie le formulaire de connexion ;
6. provoque le throttling d'authentification ;
7. contrôle que l'adresse client vue par Waitress n'est ni celle d'Apache ni la boucle locale ;
8. détruit systématiquement la pile.

Enfin, Gitleaks analyse désormais tout l'historique Git.

Ces corrections permettent de considérer les anciens P0 Docker comme
résolus par inspection du code et de la configuration.

Le commit indique également : 966 tests réussis ; une couverture de
71,66 % ; Ruff et Bandit sans erreur.

Ces résultats sont déclarés dans le message de commit, mais le
connecteur GitHub ne retourne actuellement aucun statut ni aucune
exécution Actions pour ce SHA. Ils ne sont donc pas indépendamment
confirmés dans le présent audit.

## 2. Évaluation actualisée

| Domaine                           | Note précédente | Nouvelle note |
| --------------------------------- | --------------: | ------------: |
| Architecture applicative          |             7,2 |           7,4 |
| Qualité du code                   |             7,3 |           7,5 |
| Tests                             |             7,7 |           8,4 |
| CI et contrôles automatiques      |             7,5 |           8,8 |
| Documentation                     |             7,3 |           7,9 |
| Dépendances et reproductibilité   |             7,5 |           7,5 |
| Sécurité applicative              |             7,6 |           7,7 |
| Sécurité et fonctionnement Docker |             4,5 |           8,3 |
| Exploitation et observabilité     |             6,1 |           7,0 |

**Note globale actualisée : 7,8/10**, contre 7,1/10 précédemment.

Le gain principal provient de la fermeture des blocages Docker et de
l'ajout d'un test de bout en bout.

# 3. Blocages Docker désormais résolus

## 3.1 Vérification de pyproject.toml — résolu

Les deux scripts de démarrage vérifient désormais la présence de
`"${APP_DIR}/pyproject.toml"` et non celle de l'ancien `setup.py`.
Le conteneur n'est donc plus arrêté par un contrôle devenu
incompatible avec la nouvelle chaîne de packaging.

**Statut : résolu.**

## 3.2 Option Waitress invalide — résolu

`use_forwarded_proto` a été retirée de `production.ini`. La section
`[server:main]` ne contient maintenant que des paramètres reconnus par
Waitress :

```ini
trusted_proxy = 127.0.0.1
trusted_proxy_headers = x-forwarded-for
clear_untrusted_proxy_headers = true
use = egg:waitress#main
listen = localhost:6543
url_scheme = https
```

Un test passe les paramètres réels de cette section au constructeur
`waitress.adjustments.Adjustments`. Une future faute de frappe ou
option inconnue devrait donc être détectée avant le déploiement.

**Statut : résolu.**

## 3.3 Écoute Docker accessible depuis Apache — résolu

Les valeurs de `production.ini` restent adaptées au mode bare metal
(`listen = localhost:6543`, `trusted_proxy = 127.0.0.1`). En mode
Compose, les variables suivantes sont injectées :

```yaml
PYRAMID_LISTEN: "0.0.0.0:6543"
PYRAMID_TRUSTED_PROXY: ${ALIRPUNKTO_APACHE_IP:-172.28.10.10}
```

Le programme `apply_server_overrides.py` réécrit uniquement les
options `listen` et `trusted_proxy` dans une copie dérivée de la
configuration. Cette approche évite : de modifier le fichier de
production monté en lecture seule ; de dupliquer toute la
configuration ; de casser les chemins utilisant `%(here)s` ; d'imposer
des valeurs Docker au déploiement direct sur l'hôte.

**Statut : résolu.**

## 3.4 Proxy Apache correctement identifié — résolu

Apache reçoit une adresse fixe sur le réseau frontend
(`ipv4_address: ${ALIRPUNKTO_APACHE_IP:-172.28.10.10}`) ; le réseau
utilise par défaut `subnet: ${ALIRPUNKTO_FRONTEND_SUBNET:-172.28.10.0/24}`.
L'adresse configurée dans `PYRAMID_TRUSTED_PROXY` est donc identique à
celle du conteneur Apache. Cela permet à Waitress d'accepter le
`X-Forwarded-For` produit par Apache et au throttling de travailler
sur l'adresse du client plutôt que sur celle du proxy.

**Statut : résolu.**

**Réserve opérationnelle.** L'adresse et le sous-réseau doivent être
modifiés ensemble lorsqu'un conflit existe sur l'hôte. Cette
contrainte est documentée, mais pas validée automatiquement. Une
mauvaise combinaison provoquerait normalement un échec Compose plutôt
qu'une dégradation silencieuse.

# 4. Smoke test Docker de bout en bout

Le nouveau workflow `.github/workflows/smoke.yml` constitue
l'amélioration la plus importante de ce passage.

## 4.1 Construction et démarrage réels

Le workflow exécute `docker compose ... build` puis
`docker compose ... up -d --wait --wait-timeout 240`. Il utilise donc
les vrais Dockerfiles et le vrai fichier Compose. Cela aurait détecté
les trois anciens blocages : recherche de `setup.py` ; option Waitress
inconnue ; écoute uniquement sur la boucle locale.

## 4.2 Passage réel par Apache

Le test ne se contente pas d'appeler le port 6543 publié sur la boucle
locale. Il utilise
`curl --resolve "smoke.alirpunkto.test:443:127.0.0.1" "https://smoke.alirpunkto.test/"`.
Le nom du vhost, le SNI et le port 443 imposent un passage par Apache.
Le workflow vérifie également que la page `/login` contient le champ
`username`.

## 4.3 Vérification effective de l'adresse client

Le test récupère un jeton CSRF, puis envoie onze échecs de connexion.
Il inspecte ensuite le journal Pyramid et extrait l'adresse de
`login throttled for ip=...`. Cette adresse doit être différente de
`127.0.0.1` et de toutes les adresses du conteneur Apache. Ce test
valide donc réellement la chaîne
client → Apache → X-Forwarded-For → Waitress → request.client_addr.
Il ne s'agit pas uniquement d'un contrôle syntaxique.

## 4.4 Diagnostics et nettoyage

En cas d'échec, le workflow affiche `docker compose ps` et les 200
dernières lignes des journaux. La destruction de la pile utilise
`if: always()` et supprime également les volumes.

**Statut du smoke test : correctement conçu.**

**Limite.** Le certificat utilisé est auto-signé et les requêtes
utilisent `curl -k`. Le test valide donc le routage TLS, le vhost
HTTPS, la terminaison Apache et le proxy vers Pyramid. Il ne valide
pas l'émission réelle d'un certificat par Let's Encrypt, son
renouvellement, sa chaîne de confiance, ni le fonctionnement de
Certbot en production.

# 5. Détection de secrets — résolu

Le workflow qualité contient maintenant un job Gitleaks. Le checkout
utilise `fetch-depth: 0` : l'analyse porte donc sur l'historique
complet et pas uniquement sur l'état actuel de la branche. L'action
Gitleaks est également fixée par SHA.

**Statut : résolu.** Cette protection complète utilement Bandit,
pip-audit, Ruff, la couverture, les tests fonctionnels et le smoke
test Docker.

# 6. Tests de non-régression Docker

Le nouveau fichier `tests/test_docker_startup.py` verrouille
notamment : l'utilisation de `pyproject.toml` ; l'absence de
`use_forwarded_proto` dans tous les fichiers INI ; la validité des
options Waitress ; la conservation des valeurs bare metal ; la
modification de seulement deux lignes dans la copie générée ; le
câblage des variables Docker ; l'identité entre l'adresse Apache et le
proxy déclaré ; la présence du smoke test.

Cette combinaison est pertinente : les tests Python détectent
rapidement les régressions structurelles ; le smoke test valide le
comportement réel de la pile.

**Statut : résolu.**

# 7. Points Docker encore ouverts

## 7.1 Verrou commun au runtime, aux tests et à la qualité

L'image Pyramid installe toujours `pip install -r requirements.lock`,
or ce verrou contient désormais les extras de tests et de qualité.
L'image de production embarque donc notamment pytest, pytest-cov,
Ruff, Bandit, pip-audit, mypy et leurs dépendances.

Conséquences : image plus volumineuse ; surface logicielle plus
grande ; temps de construction accru ; davantage de dépendances à
surveiller ; présence d'outils inutiles en production.

**Statut : ouvert, sévérité moyenne.** Recommandation : produire au
minimum `requirements-runtime.lock`, `requirements-test.lock`,
`requirements-quality.lock`.

## 7.2 Image Pyramid monoétape

Le Dockerfile conserve dans l'image finale : `build-essential`,
`python3-dev`, les bibliothèques de développement LDAP, SSL, XML et
images, les outils d'installation Python. Une construction multiétape
permettrait de compiler les dépendances dans une première image et de
ne copier que le virtualenv et les bibliothèques runtime dans l'image
finale.

**Statut : ouvert.**

## 7.3 Installation hors verrou pendant la construction

Le Dockerfile exécute encore `pip install --upgrade pip setuptools
wheel` avant l'installation du verrou. Même si le verrou peut ensuite
réinstaller les versions attendues, cette étape télécharge des
versions non déterminées, augmente les accès externes pendant la
construction, et peut échouer ou changer indépendamment du dépôt.

**Statut : ouvert.**

## 7.4 Installation éditable en production

L'application est encore installée avec `pip install -e . --no-deps`.
Une installation non éditable (`pip install . --no-deps`) serait plus
adaptée à une image immuable.

**Statut : ouvert, sévérité faible à moyenne.**

## 7.5 Port Waitress publié sur la boucle locale de l'hôte

Compose publie toujours `127.0.0.1:6543:6543`. Ce port n'est pas
accessible depuis Internet, mais un processus local peut contourner
Apache, les en-têtes de sécurité ajoutés par Apache, la terminaison
TLS et certaines règles du reverse proxy. Cette exposition peut être
conservée pour le diagnostic local. En production stricte, elle peut
être retirée si elle n'est pas nécessaire.

**Statut : risque faible, décision d'exploitation.**

# 8. Constats applicatifs encore ouverts

## 8.1 Cohérence bidirectionnelle des groupes LDAP

Les échecs de modification LDAP sont désormais détectés et
journalisés, mais les deux côtés de la relation restent écrits
indépendamment (`group.uniqueMember`, `member.uniqueMemberOf`). Une
écriture peut donc réussir et l'autre échouer.

**Statut : partiellement résolu.**

## 8.2 Production du LDIF et arguments de processus

Le smoke test utilise correctement les variables
`GENERATE_LDIF_ADMIN_PW`, `GENERATE_LDIF_U1_PW`,
`GENERATE_LDIF_U2_PW` et transmet `-` dans les emplacements
correspondants. Cependant, le script interactif réel `docker/init.sh`
n'a pas été modifié par ce train de commits et continue de construire
une ligne de commande contenant les valeurs de mots de passe ou leurs
hashes. Lorsque `slappasswd` est absent, son chemin de repli peut
encore transmettre temporairement le mot de passe clair dans `argv`.
Le smoke test démontre que le mécanisme sécurisé fonctionne, mais il
ne prouve pas que `init.sh` l'utilise.

**Statut : partiellement résolu.**

## 8.3 Refresh token Keycloak dans le cookie

Le refresh token reste enregistré directement dans la session signée
(`request.session[SSO_REFRESH] = sso_token["refresh_token"]`). La
signature assure l'intégrité, pas la confidentialité.

**Statut : ouvert.**

## 8.4 Validation des réponses Keycloak

Les délais réseau et les exceptions sont correctement gérés, mais les
réponses JSON ne sont toujours pas validées avant leur utilisation :
JSON invalide ; champs manquants ; types incorrects ; valeurs
d'expiration incohérentes.

**Statut : ouvert.**

## 8.5 TLS LDAP

La configuration Docker utilise toujours LDAP sur le port 389 sans TLS
applicatif. La fabrique LDAP ne construit pas encore un objet `Tls`
imposant la validation d'un certificat et d'une autorité de confiance.
L'isolation sur le réseau Docker réduit l'exposition, mais ne remplace
pas le chiffrement et l'authentification du serveur LDAP.

**Statut : ouvert.**

## 8.6 Cache du serveur LDAP

Le premier objet `ldap3.Server` créé reste mis en cache globalement.
Les appels ultérieurs demandant un autre serveur, port, mode SSL ou
niveau d'informations peuvent encore recevoir le premier objet.

**Statut : ouvert.**

## 8.7 Rappels déclenchés par les requêtes HTTP

Le rappel des vérificateurs reste abonné à `NewRequest`. Le verrou et
l'intervalle limitent les appels dans un processus, mais ne
garantissent pas une exécution en l'absence de trafic, une
coordination entre plusieurs processus, une exécution unique après
redémarrage, ni l'absence d'impact sur la requête utilisateur.

**Statut : ouvert.**

## 8.8 .env.example incohérent

Le fichier utilise toujours `MAIL_USE_TLS`/`MAIL_USE_SSL` alors que le
code lit `MAIL_TLS`/`MAIL_SSL`. Il décrit également `LDAP_SERVER`
comme une URL complète, alors que le port est configuré séparément.

**Statut : ouvert.**

# 9. Priorités révisées

**P0 — fermé** : scripts compatibles avec `pyproject.toml` ;
configuration Waitress valide ; écoute Docker accessible ; proxy
Apache correctement déclaré ; smoke test Compose de bout en bout.

**P1 — alléger et rendre l'image reproductible** : 1. séparer les
verrous runtime, test et qualité ; 2. passer le Dockerfile Pyramid en
multiétape ; 3. supprimer la mise à niveau non verrouillée de pip,
setuptools et wheel ; 4. installer l'application en mode non
éditable ; 5. fixer les images de base par digest.

**P2 — sécurité applicative restante** : 1. activer TLS et la
validation des certificats LDAP ; 2. chiffrer le refresh token
Keycloak ; 3. valider le schéma des réponses Keycloak ; 4. finaliser
le transport hors `argv` dans `docker/init.sh` ; 5. rendre la
synchronisation LDAP cohérente ou compensée ; 6. supprimer le port
Waitress local s'il n'est pas nécessaire.

**P3 — exploitation et dette technique** : 1. sortir les rappels du
cycle HTTP ; 2. corriger `.env.example` ; 3. réduire les erreurs mypy
et rendre progressivement le job bloquant ; 4. étendre Ruff au-delà de
Pyflakes ; 5. relever progressivement le seuil de couverture ;
6. tester le cycle Certbot et le renouvellement des certificats ;
7. ajouter une CSP testée.

# 10. Conclusion

Le commit `21ebee1…` ferme correctement la principale faiblesse de
l'audit précédent : le projet ne se contente plus de tester son code
Python, il teste maintenant le produit déployé.

La combinaison suivante est particulièrement solide : tests unitaires
de la configuration Docker ; validation empirique des paramètres
Waitress ; construction des images ; démarrage Compose avec
healthchecks ; requête HTTPS à travers Apache ; vérification du
`client_addr` réel ; diagnostics sur échec ; nettoyage systématique ;
détection de secrets sur tout l'historique.

La pile Docker peut désormais être considérée comme cohérente et
déployable par conception, sous réserve de la réussite effective du
workflow dans GitHub Actions, que le connecteur utilisé pour cet audit
ne permet pas de confirmer.

Les principaux risques restants ne sont plus des blocages immédiats de
démarrage. Ils concernent maintenant surtout : la confidentialité des
tokens ; TLS LDAP ; la cohérence des écritures LDAP ; la gestion des
secrets dans `init.sh` ; la taille et la reproductibilité de l'image
de production ; les tâches périodiques ; la dette de typage.

**Évaluation actuelle : 7,8/10.**

Le projet peut atteindre environ 8,4/10 après séparation du verrou
runtime, passage à une image multiétape, sécurisation LDAP et
fermeture des constats Keycloak/LDIF.
