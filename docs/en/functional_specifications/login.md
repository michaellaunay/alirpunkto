# Login

> Status: current functional specification (replaces the historical
> scenario "Connexion d'un Membre", kept in French in
> `../../fr/specifications_historiques/Scénarios/`).
> Modules: `alirpunkto/views/login.py`, `alirpunkto/views/sso_login.py`,
> `alirpunkto/views/home.py`.

## By form (`/login`)

1. The member enters pseudonym and password.
2. The pseudonym is resolved to an `oid`; authentication is an **LDAP
   bind** (`check_password`) — no password is compared on the application
   side.
3. On success: member synchronisation from LDAP
   (`update_member_from_ldap`, recreation included if the ZODB is fresh),
   session opening (`logged_in`, lightweight `User` object), a Keycloak
   token request to align the SSO, then redirection to the page initially
   requested.
4. On failure: a neutral "invalid username or password" message (no hint
   about whether the account exists).

## By SSO (`/sso_login`)

Keycloak OIDC flow: redirect, authentication at Keycloak, return with a
code, token verification (signature, audience, expiry), then the same
synchronisation and session-opening steps. The session only keeps the
refresh token and its expiry (see
[../architecture/05_authentication.md](../architecture/05_authentication.md)).

## Open session

The home page keeps the SSO session alive while the refresh token is
valid, and logs out cleanly otherwise. `/logout` purges the session.

## Special cases

- A member present in LDAP but absent from the ZODB (rebuilt store) is
  **recreated on the fly** at their first login, type and profile
  included.
- The LDAP administrator (`is_admin`) has a dedicated path without a
  member account.
