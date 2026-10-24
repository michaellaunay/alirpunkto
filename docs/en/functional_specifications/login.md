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

## Closed accounts (#265, transversal audit of 2026-10-24, A01)

An account is **closed** when the member is in a departure state
(unsubscribed, excluded, deleted) or when the directory's `isActive`
flag is down. A closed account is refused at every door, whatever the
directory still accepts as a bind: the LDAP login, the SSO callback, a
password-reset request (same neutral answer as an unknown address, no
state change, no e-mail), an old reset link (answered as obsolete) and
a reset session armed before the departure. The loader reads `isActive`
from the directory on every refresh, so the refusal does not depend on
the ZODB cache; and the home page treats a session as authenticated
only when the login view set both the flag and the user payload — a
stray `user` key no longer re-arms a session.

## SSO round trip (transversal audit of 2026-10-24, A04)

The departure to Keycloak arms the browser session with a one-time
`state` and a PKCE verifier (S256), both time-stamped. The callback
consumes them once: a `code` that comes back without the matching,
unexpired `state` is not exchanged at all, and the exchange carries the
verifier. The access token is then verified against a fixed algorithm
list (`KEYCLOAK_JWT_ALGORITHMS`, `RS256` by default) and the realm's
issuer (`KEYCLOAK_ISSUER`, else `<server>/realms/<realm>`) — never
against the algorithm announced in the token's own header. The direct
LDAP login stays available: Keycloak is never the only door.
