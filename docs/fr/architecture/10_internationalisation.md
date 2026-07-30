# Internationalisation

> Statut : documentation courante.
> Modules : `alirpunkto/locale/`, `alirpunkto/constants_and_globals.py`
> (`TranslationStringFactory`), outils `tools/translate*.py`.

## Portée

AlirPunkto est traduit dans plus de trente langues européennes (dossier
`alirpunkto/locale/` : catalogue `alirpunkto.pot` et un dossier par locale,
de `bg` à `uk`, espéranto compris). Les chaînes sont déclarées via la
fabrique `_ = TranslationStringFactory('alirpunkto')` et les valeurs des
énumérations métier sont elles-mêmes des clés de traduction
(`member_types_cooperator_value`, `candidature_states_pending_value`, …).

## Langue servie

Chaque membre déclare jusqu'à trois langues (`preferredLanguage`,
`secondLanguage`, `thirdLanguage`, stockées dans LDAP et reflétées dans
`MemberDatas.lang1..lang3`). Deux mécanismes distincts s'appuient dessus
(#204) :

- **interface** : le `locale_negotiator` (`alirpunkto/__init__.py`) applique
  `_LOCALE_` explicite (paramètre ou cookie) >
  `session['preferred_language']` > `Accept-Language`. La session est posée
  à trois points d'entrée : à la connexion, dès que le candidat soumet sa
  `lang1` à l'inscription, et après une modification réussie de sa propre
  langue dans `modify_member` ;
- **courriels** : la langue déclarée du **destinataire** prime
  (voir [07_messagerie](07_messagerie.md)).

Le rendu des courriels d'inscription dans toutes les locales et pour tous
les types de membres est verrouillé par la suite de tests i18n.

## Interpolation dans les gabarits

Dans les gabarits Chameleon, `_` est `auto_translate`
(`alirpunkto/__init__.py`) : la traduction fusionne
`SITE_INFORMATION_MAPPING` (site_name, domain_name, organization_details,
les URL d'espace de travail, de souscription de parts et de cotisation,
`forgetting_time_constant`) avec le *mapping* local de l'appel — les
`${...}` des catalogues sont donc substitués partout sans répéter les
variables de site à chaque appel (#223, #236). Les valeurs sont résolues
**au moment du rendu** depuis les réglages `.ini` (`site_name`,
`domain_name` — le nom d'affichage de la plateforme —, `site_url`,
`organization_details`, …), les constantes d'environnement ne servant que
de repli : les descriptions de champs du formulaire, qui capturent le
mapping à l'import, suivent elles aussi la configuration du déploiement
(#223 rouvert, #242). Un rendu en `structure`
est requis quand le catalogue porte du HTML (listes, paragraphes).

## Chaîne de traduction

Le catalogue `.pot` est extrait du code ; les `.po` par langue sont
complétés, au besoin avec l'aide des scripts `tools/translate*.py`
(traduction assistée), puis compilés en `.mo`. Voir
`tools/TRANSLATION_I18N_SCRIPTS_README.md`.

**Piège opérationnel** : les `.mo` compilés sont versionnés et c'est eux
que lit le *localizer* — modifier un `.po` sans le recompiler (`msgfmt`)
ne change rien à l'exécution. La parité `.po`/`.mo` des messages sensibles
est verrouillée par des tests qui passent par le vrai *localizer* (#207).

## Limites connues

- Les traductions non techniques de certaines locales restent partielles ;
  le repli vers l'anglais ou le français s'applique alors.
- Les gabarits localisés (`locale/*/LC_MESSAGES/*.pt`) sont du Chameleon :
  les guillemets **typographiques** (« », “ ”, ‚ ') n'ont pas leur place
  dans les attributs TAL — chaque langue tend à y « localiser » ses
  guillemets lors de traductions assistées, ce qui casse la compilation ;
  le rendu réel de chaque gabarit de résultat est testé pour l'empêcher
  (#235).

## Identifiants symboliques et maintenance du `.pot` (2026-07-30)

Les chaînes introduites par les campagnes récentes utilisaient
transitoirement le texte anglais comme `msgid` ; elles ont été renommées en
**identifiants symboliques** (`upgrade_to_cooperator_button`, etc.),
propagés aux **33 catalogues** avec repli anglais explicite, et le
`alirpunkto.pot` a été remis à niveau. La règle de maintenance : toute
nouvelle chaîne naît avec un `msgid` symbolique, une entrée dans le `.pot`,
sa traduction anglaise et française, et les `.mo` versionnés sont
recompilés (`msgfmt`) dans le même commit. Les libellés du catalogue
d'applications (`applications.ini`) sont eux aussi des `msgid` résolus au
rendu.
