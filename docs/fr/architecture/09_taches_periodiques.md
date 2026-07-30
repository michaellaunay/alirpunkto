# Tâches périodiques

> Statut : documentation courante.

## État actuel : pas d'ordonnanceur applicatif

L'application **n'embarque aucun ordonnanceur** : le `@TODO` de 2023 du
journal de conception (intégrer `pyramid_scheduler`) n'a jamais été réalisé.
Les échéances sont vérifiées **au moment de l'accès** :

- l'échéance du jeton de rafraîchissement SSO est contrôlée par `home_view`
  à chaque visite (voir [05_authentification](05_authentification.md)) ;
- les états de candidature n'évoluent que sous l'action d'un utilisateur ou
  d'un vérificateur.

## Tâches planifiées hors application

La pile Docker assure les travaux récurrents :

- **sauvegardes** : `docker/backup.sh` sauvegarde la configuration et les
  données (annuaire, ZODB) ; sa planification et sa restauration sont
  décrites dans `docker/README.md` (section « Backups ») ;
- renouvellement TLS et supervision Postfix relèvent aussi de la pile
  (audit Docker de 2026).

## Limites connues et évolutions envisagées

Deux traitements périodiques existent désormais comme **fonctions
utilitaires appelables** — le dépôt reste sans ordonnanceur applicatif, et
c'est un choix : la planification appartient à l'exploitation
(2026-07-30).

## Purge post-quarantaine

`utils.purge_unsubscribed_members(request, now=None)` parcourt les membres
`UNSUBSCRIBED` dont `data.date_erasure_all_data` est échue : l'entrée LDAP
est supprimée, les données personnelles effacées (seuls **le pseudonyme, la
date et le motif du départ** subsistent), le membre passe à `DELETED`, et
l'ancien membre est informé par courriel (#54). Idempotente ; retourne les
oid purgés.

## Scan quotidien des groupes dynamiques

`dynamic_groups.daily_group_scan(request, today=None)` re-synchronise tous
les membres des groupes gérés : c'est lui qui transforme le **temps
calendaire** (cotisation annuelle échue ou renouvelée) en transitions
(#148). Idempotent ; retourne les oid dont les groupes ont changé.

## Branchement

Les deux s'appellent ensemble, une fois par jour, depuis un `cron` (ou un
timer systemd) via un petit script utilisant `pyramid.paster.bootstrap`
avec le `production.ini` de l'instance — par exemple :

```python
from pyramid.paster import bootstrap
from alirpunkto.utils import purge_unsubscribed_members
from alirpunkto.dynamic_groups import daily_group_scan

with bootstrap("production.ini") as env:
    request = env["request"]
    purge_unsubscribed_members(request)
    daily_group_scan(request)
```

L'expiration des demandes de démission non confirmées n'a pas besoin de
tâche : elle est **paresseuse** (vérifiée au profil et au clic du lien).

## Limites connues et évolutions envisagées

Ni purge des candidatures périmées ni relance automatique des courriels en
erreur : ces opérations restent manuelles. Un point d'entrée console
(`console_scripts`) empaquetant le script ci-dessus est l'évolution
naturelle ; la décision sera consignée dans
[decisions_architecture](decisions_architecture.md) lorsque tranchée.
