# E-mail

> Status: current documentation.
> Modules: `alirpunkto/utils.py` (`send_email` and callers), the `[mail]`
> configuration of the `.ini` files, the Postfix stack (`docker/`).

## Sending chain

Application e-mails (address validation, invitations to vote, candidature
state notifications, password reset, address change) are built in
`alirpunkto/utils.py` and handed to **pyramid_mailer**. Sending is
**transactional**: the message only leaves at the request's *commit*
(`pyramid_tm`), never for a state that was not persisted.

The relay is a local **Postfix** (`mail.host = localhost`,
`mail.port = 25`): the Postfix container of the Docker stack in
production, or the host's Postfix on a bare-metal deployment. The hardened
configuration (no open relay, port 25 unpublished, DKIM/SPF/DMARC) is
described in `docker/README.md`.

## Delivery tracking

Each `Member` keeps `email_send_status_history`: a list of `EmailEvent`
whose status follows `EmailSendStatus` (`IN_PREPARATION`, `SENT`, `ERROR`).
This journal makes non-delivery diagnosable without digging through the
Postfix logs.

## Localisation

E-mails are rendered in the **recipient's declared language**:
`get_preferred_language(request, member)` returns `data.lang1` (LDAP alias
`preferredLanguage`) when supported, otherwise the request's
`Accept-Language`, and `get_local_template` resolves the matching template
with an English fallback. The four sending helpers pass their recipient: a
candidate who chose German receives German e-mails even when the sending is
triggered from a French browser (#204).

Special cases:

- the **subjects** of the verifier e-mails are translated in the language of
  **each** verifier through `_translate_for_language`
  (`views/register.py`, #238);
- the **result** e-mails (approval, rejection) exist in the seven main
  languages (de, en, es, fr, it, nl, pl) and the pending-verification e-mail
  (`send_candidature_pending_email`) in English and French; other locales
  fall back to English;
- callers pass the template name explicitly by keyword
  (`template_name=...`) — a misplaced positional once silenced the welcome
  e-mail (#213).

See [10_internationalization](10_internationalization.md); rendering every
result template in both modes (`textual` text/HTML) is locked by the test
suite.

## Sender details

The e-mail footer carries the postal address `organization_details`, read
from the `.ini` setting with a fallback to the `ORGANIZATION_DETAILS`
environment constant — the value is never empty, and its absence was a
spam-flagging factor (#169). Messages referencing `${administrator}` get
`ADMIN_EMAIL` in their mapping (#81).

## Known limits

- No persistent queue on the application side: if Postfix refuses
  durably, the `ERROR` event is journaled but no automatic retry exists.
