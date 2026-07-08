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
applications.sympa.logo_file = static/sympa.png
```

These entries are grouped at start-up and exposed to the views through
`request.registry.settings["applications"]`; `home_view` displays them with
their logo and link.

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
