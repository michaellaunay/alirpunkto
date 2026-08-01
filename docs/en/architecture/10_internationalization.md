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
`MemberDatas.lang1..lang3`). Two distinct mechanisms build on it (#204):

- **interface**: the `locale_negotiator` (`alirpunkto/__init__.py`) applies
  explicit `_LOCALE_` (parameter or cookie) >
  `session['preferred_language']` > `Accept-Language`. The session is set at
  three entry points: at login, as soon as the candidate submits their
  `lang1` during registration, and after a member successfully changes
  their own language in `modify_member`;
- **e-mails**: the **recipient's** declared language wins
  (see [07_email](07_email.md)).

Rendering the registration e-mails in every locale and for every member
type is locked by the i18n test suite.

## Interpolation in templates

In Chameleon templates, `_` is `auto_translate`
(`alirpunkto/__init__.py`): translation merges `SITE_INFORMATION_MAPPING`
(site_name, domain_name, organization_details, the workspace, share
purchase and yearly-contribution URLs, `forgetting_time_constant`) with the
call's local mapping — the `${...}` of the catalogues are substituted
everywhere without repeating the site variables at every call (#223, #236).
Values are resolved **at rendering time** from the `.ini` settings
(`site_name`, `domain_name` — the display name of the platform —,
`site_url`, `organization_details`, …), the environment constants being
only fallbacks: the form field descriptions, which capture the mapping at
import time, also follow the running deployment's configuration
(#223 reopened, #242).
A `structure` rendering is required when the catalogue carries HTML (lists,
paragraphs).

## Translation chain

The `.pot` catalogue is extracted from the code; the per-language `.po`
files are completed, if needed with the help of the `tools/translate*.py`
scripts (assisted translation), then compiled to `.mo`. See
`tools/TRANSLATION_I18N_SCRIPTS_README.md`.

**Operational trap**: the compiled `.mo` files are versioned and they are
what the localizer reads — editing a `.po` without recompiling it
(`msgfmt`) changes nothing at runtime. The `.po`/`.mo` parity of the
sensitive messages is locked by tests going through the real localizer
(#207).

## Known limits

- Non-technical translations of some locales remain partial; the fallback
  to English or French then applies.
- The localized templates (`locale/*/LC_MESSAGES/*.pt`) are Chameleon:
  **typographic** quotes (« », “ ”, ‚ ') have no place in TAL attributes —
  assisted translations tend to "localize" the attribute quotes of each
  language, which breaks compilation; the real rendering of every result
  template is tested to prevent it (#235).

## Symbolic msgids and `.pot` maintenance (2026-07-30)

Strings introduced by the recent campaigns transiently used the English
text as their `msgid`; they were renamed to **symbolic identifiers**
(`upgrade_to_cooperator_button`, …), propagated to the **33 catalogues**
with an explicit English fallback, and `alirpunkto.pot` was brought back
in line. The maintenance rule: every new string is born with a symbolic
`msgid`, a `.pot` entry, its English and French translations, and the
versioned `.mo` files recompiled (`msgfmt`) in the same commit. The
application-catalogue labels (`applications.ini`) are `msgid`s as well,
resolved at render time.

## Three lessons from the "inconsistencies" group (2026-08-01)

**The domain covers the whole template** (#175, #86):
`forgot_password.pt` carried `i18n:domain="alirpunkto"` on an inner div —
the title and the instruction, outside its scope, were looked up in the
default domain and fell back to the inline English in every language,
translations present or not. The domain sits on the slot root; it was
the only template in the repository with that hole (scan done).

**Variables go through `_()`** (#160): Chameleon's native
`i18n:translate`/`i18n:name` pipeline does not interpolate the `${...}`
placeholders of the msgstr — `check_new_email.pt` displayed a literal
`${domain_name}`. Messages with variables render through
`tal:content="python:_('msgid', {'key': value})"`: `auto_translate`
merges the site mapping and the passed keys (`admin_email` is not in
`SITE_INFORMATION_MAPPING`).

**The link bearer's language** (#248): the change-password screen,
reached through the e-mailed link without a session, displays in the
member's preferred language — `switch_request_language` (#247) as soon
as the token has validated the seed. Never on the anonymous leg: a
switch there would betray that the account exists.
