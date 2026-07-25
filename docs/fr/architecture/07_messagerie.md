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

Les courriels sont rendus dans la **langue déclarée du destinataire** :
`get_preferred_language(request, member)` retourne `data.lang1` (alias LDAP
`preferredLanguage`) quand elle est supportée, sinon l'`Accept-Language` de
la requête, et `get_local_template` résout le gabarit correspondant avec
repli anglais. Les quatre fonctions d'envoi passent leur destinataire : un
candidat qui a choisi l'allemand reçoit ses courriels en allemand, même si
l'envoi est déclenché depuis un navigateur français (#204).

Cas particuliers :

- les **sujets** des courriels aux vérificateurs sont traduits dans la
  langue de **chaque** vérificateur via `_translate_for_language`
  (`views/register.py`, #238) ;
- les courriels de **résultat** (approbation, refus) existent dans les sept
  langues principales (de, en, es, fr, it, nl, pl) et le courriel d'attente
  de vérification (`send_candidature_pending_email`) en anglais et en
  français ; les autres locales retombent sur l'anglais ;
- le nom du gabarit est passé explicitement par mot-clé
  (`template_name=...`) par les appelants — un positionnel mal placé rendait
  jadis le courriel d'accueil muet (#213).

Voir [10_internationalisation](10_internationalisation.md) ; le rendu de
chaque gabarit de résultat dans les deux modes (`textual` texte/HTML) est
verrouillé par la suite de tests.

## Coordonnées de l'expéditeur

Le pied des courriels porte l'adresse postale `organization_details`, lue
du réglage `.ini` avec repli sur la constante d'environnement
`ORGANIZATION_DETAILS` — la valeur n'est jamais vide, et son absence était
un facteur de classement en pourriel (#169). Les messages qui référencent
`${administrator}` reçoivent `ADMIN_EMAIL` dans leur *mapping* (#81).

## Limites connues

- Pas de file d'attente persistante côté application : si Postfix refuse
  durablement, l'événement `ERROR` est journalisé mais aucune relance
  automatique n'existe.
