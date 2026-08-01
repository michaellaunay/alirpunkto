# Audit externe du dépôt (ChatGPT) — 1ᵉʳ août 2026

**Provenance.** Audit statique du dépôt public réalisé par ChatGPT à la
demande de Michaël Launay. Note globale proposée : **6,5/10**. Le texte
intégral est reproduit en seconde partie de ce document.

**Statut.** Contre-expertisé sur pièces le jour même (chaque constat
majeur vérifié contre le code du master) ; plan d'action en trois
paquets adopté, avec trois décisions d'architecture actées. Les
correctifs du paquet A sont livrés au fil de l'eau (patchs 0063+).

## Contre-expertise

L'audit est **largement exact** : la vérification sur pièces a confirmé
la quasi-totalité des constats, y compris dans le détail — l'import
parasite `from httpcore import request` (login.py l.7), la **redirection
ouverte** après connexion (`session['redirect_url']` suivi sans
validation, l.87-90), l'absence totale de limitation des tentatives, le
cache `Server` LDAP global aveugle à ses paramètres, les trois appels
`encrypt_secret_for_logs` en `log.debug`, le refresh token dans le
cookie de session signé, les dépendances toutes non bornées avec
`version='0.0'` sans verrou, la CI réduite au seul job de tests, les
doublons d'imports, le rappel des vérificateurs abonné à `NewRequest`,
le LDAP interne en clair sur le compose de test, et les booléens mail
véhiculés en chaînes.

Trois nuances mesurées. **La couverture réelle est de 70 %** (4052
lignes) : le seuil `fail-under=80` recommandé est un objectif, pas
l'état — il s'applique en cliquet (68 d'abord, montée progressive). **La
suite de tests est sous-créditée** : ~900 tests avec démonstrations
rouges systématiques et verrous structurels ; la critique valide porte
sur l'absence de lint et de couverture *en CI*, pas sur la suite. **Le
rappel des vérificateurs** : l'audit converge avec la documentation
maison (chapitre 09) — le déplacement vers le `cron` était déjà la
cible.

## Décisions actées

1. **Les journaux de mots de passe chiffrés sont conservés.** Le
   chiffrement en niveau DEBUG — RSA-OAEP/SHA-256 vers une clé
   publique fournie par l'environnement, la clé privée restant hors du
   serveur — est un outil de diagnostic de la
   chaîne complète, assumé sous la responsabilité de l'administrateur :
   son déclenchement exige une intention précise (niveau de log, lecture
   du code et de la documentation), et un administrateur malveillant
   pourrait tout aussi bien modifier le code silencieusement. Le
   chantier de suppression est abandonné.
2. **Les globales de `constants_and_globals` sont un choix voulu.** Le
   point « couplage excessif » de l'audit est écarté ; la question du
   découpage de `__init__.py` reste distincte.
3. **Keycloak ne deviendra pas l'unique point d'authentification.** Le
   serveur de test n'est pas relié à Keycloak et n'héberge
   qu'AlirPunkto — non l'ensemble des applications Cosmopolitical.
   L'authentification LDAP directe est une voie assumée de
   l'architecture, pas une dette ; l'intégration Keycloak reste ce
   qu'elle est aujourd'hui : l'obtention d'un jeton SSO après
   l'authentification locale.

## Plan d'action retenu et état d'avancement

**Paquet A — correctifs immédiats (patchs livrés au fil de l'eau)** :
la redirection ouverte (0063 : `safe_local_redirect`, cibles du site
uniquement) ; la limitation des tentatives de connexion (0064 : fenêtres
glissantes IP et identifiant avant tout accès LDAP, `trusted_proxy`
waitress — sans lui la fenêtre IP serait globale derrière Apache) ; les
dépendances bornées et verrouillées (0065 : `pyproject.toml`,
`requirements.lock` de 77 paquets, CI réindexée) ; puis la CI qualité
(ruff, bandit, pip-audit, couverture en cliquet à 68), les correctifs
ciblés (cache `Server` indexé, booléens mail, rappel des vérificateurs
déplacé vers le cron du chapitre 09) et le chiffrement du refresh token
dans le cookie.

**Paquet B — décisions d'infrastructure** : TLS sur le LDAP interne,
en-têtes de sécurité du vhost Apache (HSTS, CSP, remplacement des
`X-Forwarded-*`), remplacement du montage `.env` par des variables
ciblées, images par digest et scan, sauvegardes testées ZODB/LDAP.

**Paquet C — structurant** : sessions côté serveur, examen du compte
administrateur spécial, découpage éventuel de `__init__.py` — sans
Keycloak-unique (décision 3).

---

# Texte intégral de l'audit

## Conclusion générale

**Appréciation globale : 6,5/10**

Le projet présente une architecture cohérente et une nette amélioration récente sur la conteneurisation, l'isolation réseau, la protection CSRF, les cookies et la gestion des secrets. La documentation d'exploitation est supérieure à celle de nombreux projets comparables.

En revanche, plusieurs éléments empêchent encore de considérer AlirPunkto comme suffisamment durci pour une application exposée publiquement et manipulant des identités :

| Domaine                      |   Note | Appréciation                                                   |
| ---------------------------- | -----: | -------------------------------------------------------------- |
| Architecture                 |   7/10 | Cohérente, mais fortement couplée                              |
| Qualité du code              |   6/10 | Fonctionnel, mais dette technique visible                      |
| Tests et CI                  | 6,5/10 | Bonne base, contrôles qualité incomplets                       |
| Documentation                | 7,5/10 | Riche, parfois dispersée ou ambiguë                            |
| Gestion des dépendances      | 3,5/10 | Principal point faible                                         |
| Sécurité applicative         |   6/10 | Protections globales présentes, faiblesses ciblées importantes |
| Sécurité Docker              | 7,5/10 | Bon niveau de durcissement                                     |
| Exploitabilité/observabilité |   6/10 | Correcte, mais plusieurs risques opérationnels                 |

## Constats prioritaires

### Critique — Dépendances non versionnées

Toutes les dépendances sont déclarées sans version minimale, maximale ou verrouillée. Cela signifie que deux installations faites à des dates différentes peuvent produire des environnements différents. Une mise à jour majeure incompatible ou une version compromise pourrait être installée automatiquement. Il n'existe pas non plus de fichier de verrouillage ni de génération reproductible des dépendances.

**À faire immédiatement :** migrer les métadonnées vers `pyproject.toml` ; définir des contraintes compatibles ; générer un verrou avec `pip-tools`, `uv` ou Poetry ; séparer dépendances d'exécution, de test et de développement ; automatiser `pip-audit` ; activer Dependabot ou Renovate. Le verrou doit être commité et régénéré volontairement.

### Élevé — Redirection ouverte après authentification

Après connexion, l'application récupère directement une URL placée en session puis redirige l'utilisateur. Aucune validation visible n'impose que l'URL soit interne, relative ou rattachée au domaine AlirPunkto. Un attaquant pourrait potentiellement construire un parcours dans lequel la victime visite une URL préparée, est redirigée vers la connexion, se connecte, puis est redirigée vers un domaine contrôlé par l'attaquant. Cela facilite le phishing post-authentification.

**Correction :** valider que la cible est locale (ni schéma, ni autorité, chemin commençant par `/` mais pas `//`) ; ne stocker idéalement que le nom de route et ses paramètres, plutôt qu'une URL libre.

### Élevé — Absence visible de limitation des tentatives de connexion

La vue de connexion effectue directement une authentification LDAP, sans limitation par compte ou par adresse IP. Cela expose le service au brute force, au credential stuffing, à une saturation de l'annuaire LDAP et à des attaques distribuées contre le compte administrateur.

**Recommandation :** limitation courte par IP (par exemple 10 tentatives sur 5 minutes) ; limitation plus stricte par identifiant ; délais progressifs ; réponse identique pour compte inexistant et mot de passe invalide ; journalisation structurée sans mot de passe ; blocage ou challenge supplémentaire après anomalie.

### Élevé — Authentification LDAP potentiellement en clair

La fabrique LDAP prend en charge SSL, mais la pile Docker configure le port 389 sans SSL. Dans la configuration actuelle, les mots de passe semblent pouvoir circuler en LDAP simple sur le réseau Docker interne. Ce réseau est isolé, ce qui réduit fortement l'exposition, mais ne fournit ni confidentialité ni authentification cryptographique entre Pyramid et OpenLDAP.

**Recommandation :** activer StartTLS ou LDAPS ; vérifier le certificat LDAP ; ne jamais utiliser `CERT_NONE` ; interdire le bind simple sans TLS côté OpenLDAP ; ajouter un test d'intégration garantissant l'échec du démarrage si TLS est obligatoire mais indisponible.

### Élevé — Mot de passe réutilisé vers Keycloak

Après authentification LDAP, le mot de passe fourni est transmis à `get_keycloak_token(user, password)`. Cela ressemble à un flux Resource Owner Password Credentials où l'application collecte le mot de passe pour le transmettre à un second fournisseur d'identité. Risques : augmentation du nombre de composants manipulant le mot de passe ; couplage entre LDAP et Keycloak ; compromission plus grave en cas de faille applicative ; incompatibilité avec MFA, WebAuthn et les politiques modernes d'identité.

**Architecture recommandée :** Keycloak comme point d'entrée via Authorization Code + PKCE ; LDAP fédéré ou synchronisé derrière Keycloak ; AlirPunkto ne reçoit plus jamais le mot de passe ; rotation et invalidation correctes des refresh tokens ; contrôle strict de `state`, `nonce`, `iss`, `aud` et de l'algorithme JWT.

### Élevé — Session entièrement stockée côté client

L'application utilise `SignedCookieSessionFactory`. La session est donc signée, mais pas chiffrée. Le contenu peut être lisible par le navigateur, même s'il ne peut pas être modifié sans invalider la signature. Le code indique que seuls le refresh token et son expiration sont conservés par `store_sso_tokens` ; un refresh token ne doit pas être placé dans une simple session signée côté client. Le secret de signature est dérivé par SHA-256 avant d'être fourni à Pyramid, ce qui est acceptable, et les paramètres `secure`, `httponly` et `samesite='Lax'` sont correctement activés.

**Recommandation :** utiliser une session serveur ; ne conserver dans le cookie qu'un identifiant aléatoire ; régénérer l'identifiant après authentification ; invalider la session côté serveur à la déconnexion ; stocker les refresh tokens chiffrés côté serveur ; utiliser une clé distincte par usage.

## Qualité du code

**Imports dupliqués ou inutilisés** : `from httpcore import request` dans `login.py` ; `Configurator` et `get_localizer` importés deux fois dans `__init__.py`. Cela indique qu'aucun linter strict n'est actuellement bloquant dans la CI. À ajouter : `ruff check`, `ruff format --check`, `mypy`.

**`__init__.py` beaucoup trop chargé** : le module principal assure l'initialisation des secrets, les sessions, la traduction, les rappels par courriel, la configuration LDAP, la création des groupes, le mailer, les routes et l'analyse des applications externes. Il devient un point de couplage central difficile à tester et risqué à modifier. Découpage proposé en modules `bootstrap/`, `services/`, `settings/`.

**Tâche métier exécutée lors des requêtes web** : `remind_pending_verifiers` est abonné à `NewRequest`. Chaque processus possède son propre verrou et son propre dernier passage ; un redémarrage réinitialise le délai ; plusieurs réplicas peuvent envoyer des doublons ; une tâche lente peut augmenter la latence de la requête. À remplacer par une tâche cron ou systemd, un conteneur scheduler, ou Celery/RQ/Dramatiq.

**Cache global LDAP imparfait** : la connexion n'est plus partagée — bon correctif — mais l'objet `Server` reste globalement mis en cache sans tenir compte des paramètres passés après sa première création. Correction : cache indexé par `(hostname, port, use_ssl, get_info)`.

**Typage insuffisant** : beaucoup de fonctions publiques restent non typées ; certaines valeurs de configuration sont manipulées sous forme de chaînes, notamment les ports et booléens du courrier.

## Gestion des mots de passe et secrets

**Points positifs** : le gestionnaire exige un `SECRET_KEY` non vide ; retire plusieurs secrets de l'environnement après chargement ; évite par défaut de journaliser les secrets ; stocke les mots de passe LDAP sous forme `{SSHA}` plutôt qu'en clair.

**Limites** : les secrets sont conservés dans la mémoire globale du processus ; `SECRET_KEY` semble utilisé comme secret général (une clé par usage limiterait l'impact d'une compromission) ; le format `{SSHA}` repose sur SHA-1 salé, rapide et donc peu résistant aux attaques hors ligne — privilégier Argon2id ou PBKDF2-SHA256 si le serveur OpenLDAP le permet ; même chiffrer un mot de passe pour les logs reste une pratique risquée — **recommandation forte : supprimer entièrement cette fonctionnalité** [décision : conservée, voir plus haut].

## Sécurité Docker et infrastructure

**Très bons points** : LDAP lié uniquement à `127.0.0.1` côté hôte ; Pyramid lié à `127.0.0.1:6543` ; Postfix non publié ; réseaux frontend/backend distincts ; `no-new-privileges` ; suppression de toutes les capabilities sur Pyramid ; exécution non-root ; quotas mémoire et CPU ; rotation des logs Docker ; volumes persistants ; healthchecks ; mot de passe LDAP fourni par un secret Docker ; `production.ini` monté en lecture seule.

**Améliorations nécessaires** : `read_only: true` et `tmpfs` ciblés lorsque possible ; retirer les capabilities des autres conteneurs ; fixer les images de base par digest SHA-256 ; analyser les images avec Trivy ou Grype ; générer un SBOM ; signer les images ; ajouter des sauvegardes testées pour ZODB et LDAP ; ne pas monter tout `.env` dans le conteneur Pyramid.

## Configuration HTTP et reverse proxy

`production.ini` impose l'écoute en localhost, le schéma HTTPS, les cookies `secure` et `httponly`, la durée maximale de session. Point d'attention : `use_forwarded_proto = true` — il faut s'assurer que seuls les en-têtes provenant d'Apache sont reconnus et qu'un accès direct à Waitress ne permet pas de falsifier `X-Forwarded-Proto`, `Host` ou l'adresse IP. À vérifier dans Apache : remplacement (et non simple transmission) des en-têtes `X-Forwarded-*` ; validation stricte de `Host` ; HSTS ; CSP ; `X-Content-Type-Options: nosniff` ; `Referrer-Policy` ; `Permissions-Policy` ; `frame-ancestors` ; taille maximale des requêtes ; délais et limites de connexions.

## CSRF, XSS et formulaires

L'activation globale de `require_csrf=True` est une excellente décision. Elle doit être complétée par un audit systématique : toutes les mutations en POST/PUT/PATCH/DELETE ; aucune vue destructive exemptée sans justification ; les appels AJAX transmettent le token ; les templates Chameleon échappent les contenus utilisateurs ; les expressions `structure` recensées ; les fichiers uploadés limités, inspectés et stockés hors exécution. Une protection CSRF globale ne protège ni des XSS, ni de l'IDOR, ni des redirections ouvertes, ni du brute force.

## Authentification et autorisation

La connexion distingue un compte administrateur via `is_admin(username, password)` puis utilise LDAP pour les autres comptes. Ce chemin administrateur spécial doit faire l'objet d'un contrôle spécifique : comparaison en temps constant ; stockage résistant ; impossibilité de confondre compte LDAP et compte administrateur ; MFA ; journalisation des connexions administratives. Recommandation de long terme : remplacer ce compte spécial par un rôle administrateur géré par l'IdP.

## Documentation

**Points positifs** : le README explique clairement l'objectif, la stack, la structure, l'installation, les tests, la pile Docker et la gestion des fichiers sensibles.

**Faiblesses** : environnement virtuel créé à la racine (`python3 -m venv .` — préférer `.venv`) ; documentation dispersée (plusieurs README, deux arborescences linguistiques, notes historiques) ; documents de sécurité manquants (`SECURITY.md`, politique de divulgation, modèle de menace, procédures de rotation, de réponse à incident et de restauration, matrice des données personnelles).

## Tests et CI

**Bonnes pratiques présentes** : exécution sur push et pull request ; matrice Python 3.11/3.12 ; `permissions: contents: read` ; annulation des jobs concurrents ; secrets temporaires ; rapport JUnit.

**Lacunes** : la CI ne bloque pas sur le formatage, le lint, le typage, les vulnérabilités Python, les secrets committés, les vulnérabilités Docker, l'analyse statique de sécurité, la couverture minimale. Pipeline recommandé : ruff, mypy, pytest avec couverture minimale, pip-audit, bandit, detect-secrets, semgrep, hadolint, trivy. Les actions GitHub devraient être fixées par SHA de commit.

## Maintenabilité et conception

**Points positifs** : séparation modèles/vues/templates/schémas ; annuaire LDAP encapsulé ; tests autonomes ; documentation bilingue ; commentaires souvent utiles sur les raisons des choix.

**Points négatifs** : commentaires très longs et historiques dans le code ; logique d'exploitation et logique métier mélangées ; constantes globales nombreuses [décision : choix assumé, voir plus haut] ; configuration résolue à différents endroits ; setup.py ancien, version `0.0`.

## Avis final

Le dépôt n'est pas dans un état « dangereux par défaut ». Plusieurs mesures de défense sont déjà bien conçues, particulièrement dans Docker, la CI minimale, les cookies et le CSRF. Les principaux risques actuels viennent de quatre écarts structurants : dépendances non reproductibles ; authentification fondée sur la circulation du mot de passe entre plusieurs systèmes ; sessions et jetons à vérifier ou déplacer côté serveur ; absence de contrôles automatisés de sécurité dans la CI.

Cet audit est un audit statique ciblé du dépôt accessible, pas un test d'intrusion. Il ne valide pas la configuration réelle du serveur, les valeurs de `.env`, les règles Apache finales, les permissions des volumes, ni le comportement réseau en production.
