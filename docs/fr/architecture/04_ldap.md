# Annuaire LDAP

> Statut : documentation courante.
> Modules : `alirpunkto/ldap_factory.py`, `alirpunkto/utils.py`,
> `alirpunkto/alirpunkto_schema.ldif`, `docker/migrate_ldap_legacy.py`,
> `tools/migrate_ldap_legacy_remote.py`, `tools/ldap_provision.py`.

## Rôle

OpenLDAP est le **référentiel d'identités** : comptes, mots de passe,
attributs de profil et groupes fonctionnels. L'authentification est un
*bind* LDAP ; la ZODB ne stocke jamais de mot de passe.

## Topologie

- entrées personnes à plat : `uid=<uuid>,<LDAP_BASE_DN>` (pas d'OU),
  classes `inetOrgPerson` + `alirpunktoPerson` ;
- groupes `cn=<nom>Group,<LDAP_BASE_DN>` (`groupOfUniqueNames`) ; chaque
  groupe contient au moins le membre de remplissage
  `uid=00000000-…,cn=admin,<base>` exigé par la classe ;
- l'appartenance est doublée côté personne par l'attribut applicatif
  `uniqueMemberOf` (il n'y a pas d'overlay `memberOf`).

## Schéma dédié

`alirpunkto/alirpunkto_schema.ldif` déclare 12 attributs
(`isActive`, `nationality`, `birthdate`, `secondLanguage`, `thirdLanguage`,
`cooperativeBehaviourMark(+Update)`, `numberSharesOwned`,
`dateEndValidityYearlyContribution`, `IBAN`, `uniqueMemberOf`,
`dateErasureAllData`) et la classe auxiliaire `alirpunktoPerson`
(`MUST isActive`).

## Accès depuis le code

`ldap_factory.get_ldap_server` met en cache un `Server` ldap3
(`get_info=ALL` : le schéma du serveur est chargé au bind) ;
`get_ldap_connection` rend une connexion fraîche (mock hors Docker pendant
les tests). `schema_safe_attributes(connection, attributes)` filtre les
attributs demandés que le schéma du serveur ne connaît pas : un annuaire en
retard d'un attribut ne doit jamais transformer la connexion en erreur 500
(incident du 2026-07-07, verrouillé par `tests/test_ldap_schema_tolerance.py`).

Écritures principales (`utils.py`) : `register_user_to_ldap` (création),
`update_ldap_member` (profil), `update_member_password` — toutes hachent le
mot de passe en `{SSHA}` via `secret_manager.make_ldap_password` (audit,
constat 1.3). Lecture/synchronisation : `update_member_from_ldap` reconstruit
ou met à jour le `Member` ZODB depuis l'entrée LDAP.

## Migration et provisionnement

Trois outils partagent le même pipeline d'adaptation
(`docker/migrate_ldap_legacy.py` : normalisations, réparations de
références, hachage `{SSHA}`) :

- `docker/migrate_ldap_legacy.py` : depuis un export `slapcat` ;
- `tools/migrate_ldap_legacy_remote.py` : extraction réseau via `.env` ;
- `tools/ldap_provision.py` : chaîne complète — fichier d'amorçage
  interchangeable avec `docker/initials_users.generated.ldif`, mise à niveau
  idempotente du schéma, chargement (`--install-type docker|host`), hachage
  des mots de passe en place.

Le mode d'emploi détaillé est dans `docker/README.md`.

## Limites connues

- `uniqueMemberOf` est maintenu applicativement : une modification de groupe
  faite hors application peut le désynchroniser ;
- le membre de remplissage `uid=00000000-…` doit être ignoré par tout
  traitement des groupes.
