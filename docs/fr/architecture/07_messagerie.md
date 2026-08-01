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

Les liens absolus des courriels (vote, réinitialisation, pages avec oid)
sont construits sur `get_site_url(request)` : le réglage `site_url`
(l'URL de base publique, p. ex. `https://access.cosmopolitical.coop`,
ticket #242) avec repli sur les constantes d'environnement — jamais sur
`domain_name`, qui est le **nom d'affichage** de la plateforme dans les
textes, ni sur `route_url`, qui donnerait l'hôte du mandataire local pour
les rappels envoyés hors requête utilisateur.

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

## Courriels de la démission (2026-07-30)

Trois courriels accompagnent le cycle : la **demande** (le lien de
confirmation est le vrai déclencheur ; rollback de l'état si l'envoi
échoue), l'**adieu** à la confirmation, et l'**effacement** une fois la
purge passée (#54) — pour celui-ci, l'adresse et la langue sont **capturées
avant l'effacement** (après, elles n'existent plus nulle part) et le
contenu est volontairement minimal : le pseudonyme, seul fait conservé, est
la seule donnée personnelle du message. L'envoi d'effacement est
best-effort : un incident SMTP ne fait pas échouer la purge. Gabarits en
anglais et français, repli anglais pour les autres locales.

## L'expéditeur des messages (#69, 2026-08-01)

L'expéditeur n'est jamais une personne. `resolve_mail_sender` applique
la cascade honnête que l'ancienne résolution prétendait offrir — la
variable d'environnement `MAIL_SENDER`, puis un `mail.default_sender`
non vide du `.ini` (que l'ancien code écrasait systématiquement,
jusqu'à la chaîne littérale `default_sender` employée comme expéditeur),
puis le repli générique `welcome@<domaine>`. Les résidus
(`default_sender`, `None`) valent vide ; l'unique point d'envoi lit la
valeur résolue, toute l'application suit.
