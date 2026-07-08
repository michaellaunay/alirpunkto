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

Faute d'ordonnanceur applicatif, il n'existe ni purge des candidatures
périmées, ni relance automatique des courriels en erreur, ni traitement de
`dateErasureAllData` (droit à l'effacement) : ces opérations sont
manuelles. L'intégration d'un ordonnanceur (ou de commandes `cron` dédiées
appelant des scripts `tools/`) reste l'évolution cible ; la décision sera
consignée dans [decisions_architecture](decisions_architecture.md) lorsque
tranchée.
