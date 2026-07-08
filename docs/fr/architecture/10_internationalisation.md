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
`MemberDatas.lang1..lang3`). Les pages et les **courriels** sont rendus dans
la langue préférée, avec repli — le rendu des courriels d'inscription dans
toutes les locales et pour tous les types de membres est verrouillé par la
suite de tests i18n.

## Chaîne de traduction

Le catalogue `.pot` est extrait du code ; les `.po` par langue sont
complétés, au besoin avec l'aide des scripts `tools/translate*.py`
(traduction assistée), puis compilés en `.mo`. Voir
`tools/TRANSLATION_I18N_SCRIPTS_README.md`.

## Limites connues

- Les traductions non techniques de certaines locales restent partielles ;
  le repli vers l'anglais ou le français s'applique alors.
