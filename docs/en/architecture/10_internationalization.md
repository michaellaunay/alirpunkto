# Internationalization

> Status: current documentation.
> Modules: `alirpunkto/locale/`, `alirpunkto/constants_and_globals.py`
> (`TranslationStringFactory`), tools `tools/translate*.py`.

## Scope

AlirPunkto is translated into more than thirty European languages (the
`alirpunkto/locale/` folder: the `alirpunkto.pot` catalogue and one folder
per locale, from `bg` to `uk`, Esperanto included). Strings are declared
through the factory `_ = TranslationStringFactory('alirpunkto')` and the
values of the business enumerations are themselves translation keys
(`member_types_cooperator_value`, `candidature_states_pending_value`, …).

## Language served

Each member declares up to three languages (`preferredLanguage`,
`secondLanguage`, `thirdLanguage`, stored in LDAP and mirrored in
`MemberDatas.lang1..lang3`). Pages and **e-mails** are rendered in the
preferred language, with fallback — rendering the registration e-mails in
every locale and for every member type is locked by the i18n test suite.

## Translation chain

The `.pot` catalogue is extracted from the code; the per-language `.po`
files are completed, if needed with the help of the `tools/translate*.py`
scripts (assisted translation), then compiled to `.mo`. See
`tools/TRANSLATION_I18N_SCRIPTS_README.md`.

## Known limits

- Non-technical translations of some locales remain partial; the fallback
  to English or French then applies.
