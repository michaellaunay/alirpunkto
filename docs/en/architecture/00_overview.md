# Overview

> Status: current documentation — describes the code as it is.
> See also: [01_runtime_architecture](01_runtime_architecture.md), [02_domain_model](02_domain_model.md).
> The French version (`docs/fr/architecture/`) is authoritative.

## What AlirPunkto does

AlirPunkto manages the membership life cycle of a cooperative: submission
and review of candidatures (with a humanity check, e-mail validation and a
vote by verifiers), management of members and their data, then single
sign-on (SSO) access to the cooperative's applications.

## Components

The application is a Python web application:

- **Pyramid** served by **Waitress** (`alirpunkto/__init__.py`);
- **Chameleon** TAL/METAL templates (`alirpunkto/templates/`);
- application persistence in **ZODB** (`pyramid_zodbconn`,
  `var/filestorage/Data.fs`);
- an **OpenLDAP** directory as the referential for accounts and groups,
  extended by a dedicated schema (`alirpunkto/alirpunkto_schema.ldif`);
- optional **Keycloak** for SSO (`alirpunkto/views/sso_login.py`);
- mail through **pyramid_mailer** and a **Postfix** relay;
- a **Docker** deployment stack and a local/offline test stack (`docker/`).

## The two referentials

AlirPunkto deliberately relies on two complementary stores:

1. **OpenLDAP is the identity referential**: accounts (`uid=<uuid>`),
   passwords (hashed `{SSHA}`), the `alirpunktoPerson` profile attributes
   and membership of the functional groups (`cooperatorsGroup`,
   `boardMembersGroup`, and so on).
2. **The ZODB is the application referential**: `Member` and `Candidature`
   objects (states, votes, modification journal) stored in the root
   `Members` mapping.

The code can rebuild the ZODB from LDAP (see
[03_zodb_persistence](03_zodb_persistence.md) and [04_ldap](04_ldap.md));
the converse is not true: LDAP is authoritative for identities.

## Documentation map

| Topic | Document |
|---|---|
| Request handling, routes, transactions | [01_runtime_architecture](01_runtime_architecture.md) |
| Domain model | [02_domain_model](02_domain_model.md) |
| ZODB | [03_zodb_persistence](03_zodb_persistence.md) |
| LDAP and schema | [04_ldap](04_ldap.md) |
| Authentication and SSO | [05_authentication](05_authentication.md) |
| Authorization | [06_authorization_permissions](06_authorization_permissions.md) |
| E-mail | [07_email](07_email.md) |
| Third-party applications | [08_third_party_applications](08_third_party_applications.md) |
| Periodic tasks | [09_periodic_tasks](09_periodic_tasks.md) |
| Internationalization | [10_internationalization](10_internationalization.md) |
| Security | [11_security](11_security.md) |
| Testing | [12_testing](12_testing.md) |
| Docker deployment | [13_docker_deployment](13_docker_deployment.md) |
| Developing with AI agents | [14_ai_agents](14_ai_agents.md) |
| Decisions | [architecture_decisions](architecture_decisions.md) |
| Glossary | [glossary](glossary.md) |
