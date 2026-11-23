# Tâches périodiques

> Statut : documentation courante.
> Modules : `alirpunkto/maintenance.py`, `alirpunkto/dynamic_groups.py`,
> `alirpunkto/utils.py` (`purge_unsubscribed_members`),
> `alirpunkto/keycloak_sync.py`.

## Échéances vérifiées à l'accès

Une partie des échéances est contrôlée **au moment de l'accès**, sans
tâche :

- l'échéance du jeton de rafraîchissement SSO est contrôlée par `home_view`
  à chaque visite (voir [05_authentification](05_authentification.md)) ;
- les états de candidature n'évoluent que sous l'action d'un utilisateur ou
  d'un vérificateur ;
- l'expiration des demandes de démission non confirmées est **paresseuse**
  (vérifiée au profil et au clic du lien).

## Tâches planifiées hors application

La pile Docker assure les travaux récurrents qui ne touchent pas aux
données applicatives :

- **sauvegardes** : `docker/backup.sh` sauvegarde la configuration et les
  données (annuaire, ZODB) ; sa planification et sa restauration sont
  décrites dans `docker/README.md` (section « Backups ») ;
- renouvellement TLS et supervision Postfix relèvent aussi de la pile
  (audit Docker de 2026).

## Propagation SSO en attente (audit transversal du 24 octobre 2026, A10)

Une propagation Keycloak qui échoue — serveur injoignable, fournisseur
répondant `failed > 0` ou `ignored` — laisse un fichier marqueur
(`var/keycloak_sync_pending`, surchargeable par
`KEYCLOAK_SYNC_PENDING_MARKER`). Le scan quotidien rappelle Keycloak
tant que ce marqueur existe, même un jour où aucun membre n'a changé de
groupe ; une propagation réussie le retire. Sans lui, un annuaire
convergé pendant une panne de Keycloak n'était plus propagé avant le
prochain changement sans rapport.

## La maintenance quotidienne dans l'application (#148, #269)

Le ticket #148 demande qu'AlirPunkto **scanne l'annuaire chaque jour**
(une cotisation échue fait quitter `cooperatorsGroup`, une quarantaine
terminée efface un démissionnaire) et le ticket #269 ajoute que les
membres dont le groupe dynamique a changé doivent atteindre
l'infrastructure SSO **le jour même**. Les deux traitements existaient
comme fonctions appelables, mais rien ne les appelait : la planification
avait été confiée à un `cron` externe, ce qui ne peut pas fonctionner
avec la pile livrée — le `FileStorage` de la ZODB est verrouillé par
l'application en marche, un second processus qui l'ouvre échoue
(`tools/run_upgrades.py` le dit : arrêter l'application d'abord).

La maintenance tourne donc **dans le processus de l'application**
(`alirpunkto/maintenance.py`), dans un fil d'exécution démon lancé par la
fabrique de l'application quand la configuration le demande :

```ini
daily_maintenance.enabled = true      ; false dans development.ini et testing.ini
daily_maintenance.initial_delay = 120 ; premier passage, secondes après le démarrage
daily_maintenance.interval = 86400    ; puis un passage par jour
```

Chaque passage (`run_daily_maintenance`) :

1. **purge post-quarantaine** — `utils.purge_unsubscribed_members` parcourt
   les membres `UNSUBSCRIBED` dont `data.date_erasure_all_data` est
   échue : l'entrée LDAP est supprimée, les données personnelles effacées
   (seuls **le pseudonyme, la date et le motif du départ** subsistent), le
   membre passe à `DELETED`, l'ancien membre est informé par courriel
   (#54). Le fil travaille sur le `members` de **sa propre connexion
   ZODB** (paramètre `members=`) sans relier le singleton `Members`, qui
   appartient aux fils de requêtes, et valide sa transaction lui-même ;
2. **scan des groupes dynamiques** — `dynamic_groups.daily_group_scan`
   re-synchronise tous les membres des groupes gérés **et tout Membre
   ordinaire ou Coopérateur actif de l'annuaire, même si aucun groupe ne
   le recense** (#272) : c'est lui qui transforme le **temps
   calendaire** (cotisation annuelle échue ou renouvelée) en transitions
   (#148). Être dans un groupe était jusque-là la seule façon d'être
   scanné : un membre qui les avait tous perdus — révocation passée
   alors que l'attribution était refusée, annuaire rechargé sans ses
   appartenances — n'était jamais réparé, et ne gardait aucun droit sur
   la plateforme, pas même celui de payer sa cotisation ;
3. **propagation SSO** — si au moins un membre a changé de groupe, le scan
   demande à Keycloak de ré-importer les entrées modifiées
   (`keycloak_sync.propagate_ldap_changes_to_keycloak`, voir
   [05_authentification](05_authentification.md)).

Tout est idempotent : un redémarrage qui répète un passage est sans
effet, un passage en échec ne fait que journaliser et le suivant
réessaie. Waitress étant un processus unique multi-fils, il n'y a qu'un
fil de maintenance.

## Appel manuel

Application **arrêtée** (verrou ZODB), un opérateur peut déclencher un
passage depuis un shell Python :

```python
from pyramid.paster import bootstrap
from alirpunkto.maintenance import run_daily_maintenance

with bootstrap("production.ini") as env:
    print(run_daily_maintenance(env["registry"]))
```

## Rejouer des cotisations annuelles (#272)

Quand des renouvellements facturés par la boutique en ligne n'ont jamais
atteint l'annuaire, `tools/replay_contributions.py` les rejoue depuis une
liste CSV et rétablit les groupes en un seul passage. Il ne parle qu'à
l'annuaire : l'application **continue de tourner** ; le profil en cache
de chaque membre est rafraîchi à sa prochaine connexion.

```
pseudonym,date_end_validity_yearly_contribution
SomePseudonym,2027-09-08
```

```
.venv/bin/python tools/replay_contributions.py renewals.csv          # à blanc
.venv/bin/python tools/replay_contributions.py renewals.csv --apply
```

Le passage écrit chaque date dans `dateEndValidityYearlyContribution`,
re-synchronise les groupes dynamiques de **tous** les Membres ordinaires
et Coopérateurs actifs (les membres listés redeviennent Coopérateurs,
les autres retrouvent `communityMembersGroup` et leur groupe de
candidats), puis demande à Keycloak de ré-importer les changements. Sans
`--apply`, il n'affiche que le plan. Un pseudonyme qui ne désigne aucun
Coopérateur, ou plusieurs, arrête tout avant la moindre écriture
(code 2) ; une date antérieure à celle de l'annuaire est conservée sauf
`--allow-earlier` ; un membre listé qui ne sera malgré tout pas
Coopérateur (aucune part, `isActive` à faux, sanction) est signalé. Le
code 1 signifie qu'une écriture ou une convergence a échoué : le passage
est idempotent, il suffit de le relancer.

`--reactivate` remet en plus `isActive` à vrai sur tout Membre ordinaire
ou Coopérateur — listé ou non — inactif **sans avoir démissionné**.
C'était la cause en production du #272 : les membres fondateurs avaient
été importés avec `isActive: FALSE` (`tools/cooperator_csv_to_ldif.py`)
et jamais activés, l'application les traitait donc comme démissionnaires
— aucun groupe, aucune connexion — quoi qu'ils aient payé. Une démission
enregistre toujours `dateErasureAllData` ; une entrée qui en porte une
n'est jamais réactivée. Sans l'option, le passage se contente de nommer
ces membres. La liste contient des
pseudonymes de membres : elle reste hors du dépôt (le `tmp/` ignoré par
git).

## Limites connues et évolutions envisagées

Ni purge des candidatures périmées ni relance automatique des courriels en
erreur : ces opérations restent manuelles. La décision du fil interne est
consignée dans [decisions_architecture](decisions_architecture.md)
(ADR-012).
