# Messagerie

> Statut : documentation courante.
> Modules : `alirpunkto/utils.py` (`send_email` et appelants),
> configuration `[mail]` des fichiers `.ini`, pile Postfix (`docker/`).

## Chaîne d'envoi

Les courriels applicatifs (validation d'adresse, invitations à voter,
notifications d'état de candidature, réinitialisation de mot de passe,
changement d'adresse) sont construits dans `alirpunkto/utils.py` et remis à
**pyramid_mailer**. L'envoi est **transactionnel** : le message ne part
qu'au *commit* de la requête (`pyramid_tm`), jamais pour un état non
persisté.

Le relais est un **Postfix** local (`mail.host = localhost`,
`mail.port = 25`) : le conteneur Postfix de la pile Docker en production,
ou le Postfix de l'hôte en déploiement nu. La configuration durcie
(anti-relais ouvert, port 25 non publié, DKIM/SPF/DMARC) est décrite dans
`docker/README.md`.

## Suivi d'envoi

Chaque `Member` conserve `email_send_status_history` : une liste
d'`EmailEvent` dont le statut suit `EmailSendStatus`
(`IN_PREPARATION`, `SENT`, `ERROR`). Ce journal permet de diagnostiquer les
non-réceptions sans fouiller les journaux Postfix.

## Localisation

Les courriels sont rendus dans la langue préférée du destinataire
(`preferredLanguage`), avec repli ; les gabarits et chaînes traduits sont
couverts par la suite i18n (voir
[10_internationalisation](10_internationalisation.md) et
`tests` de rendu des courriels dans toutes les locales).

## Limites connues

- Pas de file d'attente persistante côté application : si Postfix refuse
  durablement, l'événement `ERROR` est journalisé mais aucune relance
  automatique n'existe.
