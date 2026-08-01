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

## Groupes dynamiques (#148, 2026-07-30)

Les onze groupes du ticket #148 (créés au démarrage avec les trois groupes
historiques) reçoivent désormais leurs **transitions**
(`alirpunkto/dynamic_groups.py`). L'algèbre événementielle du ticket se
réduit à une **fonction pure**, `compute_target_groups`, sur quatre faits —
parts détenues, validité de la cotisation annuelle
(`dateEndValidityYearlyContribution`), sanction, rôle Board/CMA — les
groupes eux-mêmes étant l'état persistant (la sanction et le rôle se lisent
des appartenances courantes). L'applicateur `sync_member_groups` est
**idempotent** et maintient les **deux côtés** de la relation
(`uniqueMemberOf` du membre, `uniqueMember` du groupe) ; il est **best-effort
par construction** : un échec ne casse jamais l'opération appelante, le
scan quotidien rattrape. Depuis l'audit externe, chaque écriture passe
par `_checked_modify` — exception interceptée, retour vérifié,
`conn.result` journalisé avec membre, groupe, opération et côté — mais
les deux côtés restent écrits indépendamment : un échec unilatéral
peut laisser une divergence que le scan, qui lit `uniqueMemberOf`
seul, ne voit pas (cible P2 : un côté autoritatif et un scan qui
compare les deux). Il est branché aux quatre sources d'événements :
inscription (l'Ordinaire rejoint `communityMembersGroup` ; le
`ordinaryMembersGroup` **légué se vide progressivement**), approbation
d'une montée en grade (arrivée dans
`candidatesMissingShareYearContribGroup`), démission (plus aucun groupe,
l'entrée restant en quarantaine) et toute modification de profil. Les
événements de sanction et de promotion (#56/#57) ont leur crochet prêt
(`force_sanctioned`) pour les futures vues d'administration.

## Unicité d'identité et quarantaine (#54)

`is_valid_unique_identity(prénoms, noms, date de naissance)` compare
l'identité de tout candidat à **toutes** les entrées LDAP — volontairement
**sans filtre `isActive`** : l'entrée d'un démissionnaire ou exclu est
conservée pendant la Quarantaine précisément pour qu'il ne puisse pas se
réinscrire avec une réputation vierge. Le contrôle est branché aux deux
portes d'entrée Coopérateur : le formulaire d'inscription et la montée en
grade (#7).

## Avatar (`jpegPhoto`, #150)

L'avatar vit **uniquement** dans l'attribut LDAP `jpegPhoto` — ni ZODB ni
formulaire `deform` : deux vues dédiées (`member_avatar` le sert,
`avatar_upload` l'écrit), un triple contrôle (extension, nombre magique,
taille ≤ 4 Mo) et l'écriture réservée au propriétaire de la session.

## Provisions long terme (#110, #127, 2026-08-01)

Sept attributs rejoignent le schéma de référence sans qu'aucune
fonctionnalité ne les expose encore — l'**invisibilité par
construction** : ni champ `MemberDatas`, ni nœud de formulaire, ni vue,
et un test verrouille que ces noms n'atteignent jamais la surface
applicative. `tools/ldap_provision.py` les déploie en une
resynchronisation (les sondes de modernité incluent les nouveaux noms).

**L'Annuaire Partagé des Coopérateurs** (#110, §5.3.1 des statuts) :
cinq emplacements `eMailDestinationCooperator1`…`5` — la liste écrite
est **l'état entier**, les emplacements inutilisés sont vidés, aucune
adresse périmée ne survit — et `cipheredPersonalData`, un bloc unique
borné à **moins de 512 caractères** par les statuts. Le module
`shared_directory.py` fournit la chaîne complète : JSON compact, **codes
à deux lettres** pour les groupes et le rôle (les douze noms de groupes
pèsent à eux seuls plus que toute la borne), `zlib`, puis Fernet sur le
secret de session — un membre maximal mesure **440 caractères**, la
preuve que la version future peut compter sur la borne ; un bloc trop
long est refusé plutôt qu'écrit tronqué. Point noté pour la vraie
version : l'adresse d'un Coopérateur purgé peut survivre dans les
emplacements des autres.

**Le code de récupération d'identité** (#127) : l'attribut
`identityRecoveryCode` contient « une chaîne de 64 caractères » — qui
est, choix de conception documenté dans `identity_recovery.py`, le
**SHA-256 hexadécimal** de la forme canonique du code : le secret
lui-même n'est **jamais** stocké. Le code remis au membre — cinq groupes
de cinq caractères d'un alphabet sans glyphes ambigus (~122 bits) — se
recopie à la main ; la canonicalisation pardonne casse, espaces et
tirets, et la vérification est en temps constant.
