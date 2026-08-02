# Vue d'ensemble

> Statut : documentation courante — décrit le code actuel.
> Voir aussi : [01_architecture_runtime](01_architecture_runtime.md), [02_modele_domaine](02_modele_domaine.md).

## Rôle d'AlirPunkto

AlirPunkto gère le cycle de vie des adhésions d'une coopérative : dépôt et
instruction des candidatures (avec vérification d'humanité, validation de
l'adresse électronique et vote des vérificateurs), gestion des membres et de
leurs données, puis accès authentifié unique (SSO) aux applications de la
coopérative.

## Composants

L'application est une application web Python :

- **Pyramid** servie par **Waitress** (`alirpunkto/__init__.py`) ;
- gabarits **Chameleon** TAL/METAL (`alirpunkto/templates/`) ;
- persistance applicative **ZODB** (`pyramid_zodbconn`, `var/filestorage/Data.fs`) ;
- annuaire **OpenLDAP** comme référentiel des comptes et des groupes, étendu
  par un schéma propre (`alirpunkto/alirpunkto_schema.ldif`) ;
- **Keycloak** en option pour le SSO (`alirpunkto/views/sso_login.py`) ;
- messagerie via **pyramid_mailer** et un relais **Postfix** ;
- une pile **Docker** de déploiement et une pile locale de test (`docker/`).

## Les deux référentiels

AlirPunkto s'appuie volontairement sur deux stockages complémentaires :

1. **OpenLDAP est le référentiel d'identités** : comptes (`uid=<uuid>`),
   mots de passe (hachés `{SSHA}`), attributs de profil du schéma
   `alirpunktoPerson` et appartenance aux groupes fonctionnels
   (`cooperatorsGroup`, `boardMembersGroup`, etc.).
2. **La ZODB est le référentiel applicatif** : objets `Member` et
   `Candidature` (états, votes, journal des modifications) rangés dans le
   mapping racine `Members`.

Le code sait reconstruire la ZODB depuis LDAP (voir
[03_persistance_zodb](03_persistance_zodb.md) et [04_ldap](04_ldap.md)) ;
l'inverse n'est pas vrai : LDAP fait foi pour les identités.

## Carte de la documentation

| Sujet | Document |
|---|---|
| Requête, routes, transactions | [01_architecture_runtime](01_architecture_runtime.md) |
| Modèle de domaine | [02_modele_domaine](02_modele_domaine.md) |
| ZODB | [03_persistance_zodb](03_persistance_zodb.md) |
| LDAP et schéma | [04_ldap](04_ldap.md) |
| Authentification et SSO | [05_authentification](05_authentification.md) |
| Autorisations | [06_autorisations_permissions](06_autorisations_permissions.md) |
| Messagerie | [07_messagerie](07_messagerie.md) |
| Applications tierces | [08_applications_tierces](08_applications_tierces.md) |
| Tâches périodiques | [09_taches_periodiques](09_taches_periodiques.md) |
| Internationalisation | [10_internationalisation](10_internationalisation.md) |
| Sécurité | [11_securite](11_securite.md) |
| Tests | [12_tests](12_tests.md) |
| Déploiement Docker | [13_deploiement_docker](13_deploiement_docker.md) |
| Développer avec des agents IA | [14_agents_ia](14_agents_ia.md) |
| Décisions | [decisions_architecture](decisions_architecture.md) |
| Glossaire | [glossaire](glossaire.md) |
