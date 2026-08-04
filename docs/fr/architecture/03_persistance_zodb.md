# Persistance ZODB

> Statut : documentation courante.
> Modules : `alirpunkto/models/member.py` (`Members`), configuration
> `development.ini` / `production.ini`.

## Stockage

La ZODB utilise un `FileStorage` local :

```ini
zodbconn.uri = file://%(here)s/var/filestorage/Data.fs?connection_cache_size=20000
```

Les blobs et journaux vivent sous `var/` (`var/blobs`, `var/log`). Chaque
requête Pyramid obtient sa connexion via `pyramid_zodbconn` ; `pyramid_tm`
délimite la transaction et `pyramid_retry` rejoue la requête en cas de
conflit (3 tentatives).

## Racine et accès

Le seul point d'entrée applicatif est le mapping `Members`
(`root['members']`). `Members.get_instance(connection)` **relie
systématiquement l'instance à la connexion fournie** : un objet persistant
étant attaché à la connexion qui l'a chargé, réutiliser un cache issu d'une
connexion fermée provoquerait `ConnectionStateError`. La fabrique racine
appelle `get_instance` avec la connexion de la requête ; les appels sans
connexion (par exemple `generate_unique_oid`) retombent sur l'instance
courante.

## Écritures

Les vues ne commitent pas elles-mêmes : `pyramid_tm` commite en fin de
requête (les appels explicites à `transaction.commit()` ont été retirés lors
de l'audit de 2026). Les courriels confiés à `pyramid_mailer` partent au même
commit, ce qui garantit qu'aucun courriel n'annonce un état non persisté.

## Reconstruction depuis LDAP

La ZODB est reconstructible : si `var/` est supprimé puis l'application
relancée, `update_member_from_ldap` (`alirpunkto/utils.py`) recrée chaque
membre à sa première connexion à partir de l'entrée LDAP — type et profil
compris, `password`/`password_confirm` restant à `None`. Ce comportement est
verrouillé par `tests/test_zodb_repopulation_from_ldap.py` et la procédure
est décrite dans `docker/README.md` (« Repopulating the ZODB »).

## Limites connues

- `FileStorage` est mono-écrivain : l'application et les outils hors-ligne
  (`tools/purge_zodb_cleartext_passwords.py`) ne doivent pas écrire en même
  temps.
- Les candidatures refusées ou périmées restent en base ; aucune purge
  automatique n'existe (voir [09_taches_periodiques](09_taches_periodiques.md)).

## Versionnage du schéma et étapes de migration (2026-08-04)

L'annuaire LDAP est la source de vérité des membres ; la ZODB porte
l'état applicatif autour (candidatures, workflows, données membres).
Depuis le train 0087, la base est **versionnée** :
`app_root.schema_version` (0 pour une base d'avant le versionnage)
face à `SCHEMA_VERSION` attendu par le code, et chaque changement de
structure persistée voyage comme une **étape de migration**
explicite dans `alirpunkto/upgrades.py` — idempotente (rejouable
après un conflit), une par changement, dans l'esprit des upgrade
steps de GenericSetup ramené à l'essentiel.

Deux exécuteurs partagent le registre : le **paresseux** de
`root_factory` (une comparaison d'entiers par requête ; la première
requête après une mise à jour migre dans sa propre transaction,
rejouée par pyramid_retry en cas de conflit) et l'**explicite**
`tools/run_upgrades.py` pour migrer application arrêtée — recommandé
en production. Le verrou de fichier ZODB garantit l'exclusivité.

La production épinglée à `e6603d22` n'exige **aucune étape de
données** pour atteindre la version 1 : les évolutions depuis (flux
de démission) étendent le vocabulaire sans toucher aux objets
stockés ; l'étape 1 ne fait qu'estampiller.

**La voie forte** — décision du mainteneur du 2026-08-04 :
suppression de la ZODB et reconstruction depuis le LDAP, en
acceptant la perte des candidatures en attente (à l'écrasante
majorité des spams n'ayant jamais résolu le défi d'inscription).
`tools/rebuild_zodb_from_ldap.py` outille cette voie en réutilisant
la fabrique de l'application (`update_member_from_ldap`, qui crée ou
rafraîchit) : idempotent, il resynchronise une base vivante ou
reconstruit une base neuve ; la procédure de wipe complète est en
tête du script.
