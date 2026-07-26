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
