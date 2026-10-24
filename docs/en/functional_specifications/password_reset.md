# Password reset

> Status: current functional specification (replaces
> "RéinitialisationDuMotDePasse", kept in French in
> `../../fr/specifications_historiques/Scénarios/`).
> Module: `alirpunkto/views/forgot_password.py`.

## Flow

1. **Request** (`/forgot_password`) — the member enters their address or
   pseudonym. The response is identical whether the account exists or not.
2. **Token** — the site generates a reset link containing the **encrypted**
   `oid` together with a **seed**; the event is journaled in the member's
   `email_send_status_history` and the e-mail leaves through
   `send_email_to_member` (transactional sending).
3. **Return** — on click, the site decrypts the token (`decrypt_oid`) and
   only accepts the request if the seed matches the **latest** journaled
   sending: any earlier link is invalidated by a newer one.
4. **New password** — entry and confirmation (`is_valid_password` rules),
   then LDAP write through `update_member_password` with `{SSHA}` hashing;
   nothing is kept in cleartext.

## Security properties

- no account enumeration (constant response);
- effectively single-use link (seed of the latest event);
- the secret only travels encrypted in the URL and is never stored in
  cleartext.

## The link as a capability (transversal audit of 2026-10-24, A05)

A reset link is a capability for one purpose and one emission. Opening
it requires that the member's last e-mail event still carries its seed
**and** was recorded for a password reset — an address-change or
resignation link of the same member opens nothing. Opening it binds the
session to that seed; a newer reset request moves the seed and kills the
older armed session; the password change consumes the link, so a second
POST with a copy of the armed cookie is refused. A closed account is
refused at every one of these steps (A01).

## Known limits

- The link has no expiry of its own in time: it is only invalidated by a
  later sending. An explicit deadline would be a simple improvement.
