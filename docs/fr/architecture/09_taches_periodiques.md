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
   re-synchronise tous les membres des groupes gérés : c'est lui qui
   transforme le **temps calendaire** (cotisation annuelle échue ou
   renouvelée) en transitions (#148) ;
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

## Limites connues et évolutions envisagées

Ni purge des candidatures périmées ni relance automatique des courriels en
erreur : ces opérations restent manuelles. La décision du fil interne est
consignée dans [decisions_architecture](decisions_architecture.md)
(ADR-012).
