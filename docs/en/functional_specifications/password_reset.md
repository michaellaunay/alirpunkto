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

## Known limits

- The link has no expiry of its own in time: it is only invalidated by a
  later sending. An explicit deadline would be a simple improvement.
