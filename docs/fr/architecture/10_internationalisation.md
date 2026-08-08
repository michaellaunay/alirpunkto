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

## Trois leçons du groupe « incohérences » (2026-08-01)

**Le domaine couvre tout le gabarit** (#175, #86) : `forgot_password.pt`
portait `i18n:domain="alirpunkto"` sur un div intérieur — le titre et
l'instruction, hors de sa portée, étaient cherchés dans le domaine par
défaut et retombaient sur l'anglais inline dans toutes les langues,
traductions présentes ou non. Le domaine se pose sur la racine du slot ;
c'était le seul gabarit troué du dépôt (balayage fait).

**Les variables passent par `_()`** (#160) : le pipeline natif
`i18n:translate`/`i18n:name` de Chameleon n'interpole pas les `${...}`
des msgstr — `check_new_email.pt` affichait `${domain_name}` littéral.
Les messages à variables se rendent par
`tal:content="python:_('msgid', {'clé': valeur})"` : `auto_translate`
fusionne le mapping du site et les clés passées (l'`admin_email` n'est
pas dans `SITE_INFORMATION_MAPPING`).

**La langue du porteur de lien** (#248) : l'écran de changement de mot
de passe, atteint par le lien e-mail sans session, s'affiche dans la
langue préférée du membre — `switch_request_language` (#247) dès que le
token a validé le seed. Jamais sur la jambe anonyme : une bascule y
trahirait l'existence du compte.

## Audit i18n et remise en état (2026-08-08, train 0098)

Un audit externe thématique du sous-système locale
(`docs/fr/audits/20260808_audit_externe_chatgpt_i18n_locale.md` —
infrastructure 8/10, traductions 5/10) a établi que 21 msgid
récents manquaient dans 31 des 33 catalogues : des clés symboliques
brutes pouvaient atteindre l'écran. Le train 0098 a exécuté la
remise en état structurelle : **651 entrées de fallback anglais
explicite non-fuzzy** synchronisées (commentées « English fallback
pending translation »), les **33 `.mo` recompilés** sous
`msgfmt --check-format`, la découverte de locales restreinte aux
répertoires réels, et le verrou `tests/test_locale_completeness.py`
qui grave l'état : couverture POT complète de chaque catalogue,
clés de l'audit présentes dans chaque `.mo` compilé, et **cliquets**
sur les dettes (747 fuzzy, 136 vides — elles ne peuvent que
décroître : traduire réellement, ou anglais explicite, jamais
fuzzy). L'outillage `tools/translate.py`/`translate.sh` a été durci
séparément (validation msgfmt, rapports, écriture atomique).

Restent ouverts au mainteneur (recommandations de l'audit) : le
registre unique des langues dont tout dériverait, le sort des huit
locales non proposées par le formulaire (`be bs is no sq sr tr
uk`), les niveaux de support (Tier 1/2/3), la matrice des templates
de mails, l'assainissement du POT, et la campagne de traduction
réelle — l'espéranto en premier.

## Registre unique des langues (2026-08-08, train 0099)

`SUPPORTED_LOCALES` (dans `constants_and_globals.py`) est désormais
**la** source de vérité : 33 langues, chacune avec son nom natif,
son drapeau `selectable` (le formulaire propose exactement la
tranche sélectionnable — les huit locales jamais offertes le sont
maintenant **explicitement** : inverser le booléen est toute la
décision) et son `tier` (niveaux de l'audit : 1 complet — `en`,
`fr` —, 2 fonctionnel — `de es it nl pl` —, 3 expérimental).
`EUROPEAN_LOCALES` et `get_locales()`/`AVAILABLE_LANGUAGES` en sont
des **dérivations** — neutralité prouvée octet pour octet à la
migration. Ajouter une langue = une entrée au registre **et** son
répertoire `locale/<code>/` : le verrou de complétude impose la
bijection registre↔disque et la couverture POT du nouveau
catalogue. Plus jamais quatre listes indépendantes.

### Mise à jour (2026-08-08, train 0100) : les huit orphelines sont proposées

Décision du mainteneur (option 1 de l'audit §22) : `be bs is no sq
sr tr uk` passent `selectable: True`. Le formulaire propose donc les
**33 langues** — les huit rejoignent la fin de la liste, l'ordre
historique des 25 est intact. Le geste est sûr depuis le train
0098 : couverture POT complète et `.mo` frais garantis par les
verrous ; le pire cas est un fallback anglais, comme pour toute
langue de tier 3. Un verrou grave la décision : retirer une langue
du sélecteur redevient un acte explicite du registre.
