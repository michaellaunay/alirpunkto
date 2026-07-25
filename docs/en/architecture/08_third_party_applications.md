# Third-party applications

> Status: current documentation.
> Modules: `alirpunkto/views/home.py`, `.ini` configuration
> (`applications.*`), `alirpunkto/views/sso_login.py`.

## Principle

AlirPunkto is the members' entry point to the cooperative's services
(mailing lists, forums, tools). Applications are not hard-coded: they are
**declared in the configuration** and shown on the home page to logged-in
members.

## Declaration

Each application is described by prefixed keys in the `.ini` file:

```ini
applications.sympa.name = Sympa
applications.sympa.id = sympa
applications.sympa.logo_file = static/sympa.png
applications.sympa.url = https://lists.example.coop/sso/keycloak
applications.sympa.description = Mailing lists
applications.sympa.explanation = Manage your list subscriptions.
```

These entries are grouped at start-up and exposed to the views through
`request.registry.settings["applications"]`; `home_view` displays them with
their logo and link. Two field-tested rules (#142, #147):

- `url` must be the application's **SSO entry URL** (the Keycloak
  endpoint), not its generic login page — otherwise the member lands on a
  password form they do not have;
- the `explanation` is displayed as text under the link (no longer a
  tooltip), and every link opens in a new tab
  (`target="_blank" rel="noopener noreferrer"`).

The `name`, `id`, `logo_file` and `url` keys are **required**:
`__init__.py` silently drops any incomplete application. Structural
invariant tests check the repository `.ini` files (parsable declarations,
required keys, absolute URLs) without freezing deployment-specific
values.

## Unified access

Access to the applications relies on SSO: third-party applications are
**Keycloak** clients, backed by the same OpenLDAP directory as AlirPunkto.
A member logged into AlirPunkto is therefore recognised by the applications
without typing a password again (see
[05_authentication](05_authentication.md)).

## History

The initial scenarios "Liste des Applications" and "Configuration de la
liste des applications" are archived (in French) under
`../../fr/specifications_historiques/Scénarios/`; this document and the
upcoming functional specification replace them.
