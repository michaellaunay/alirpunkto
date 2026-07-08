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

E-mails are rendered in the recipient's preferred language
(`preferredLanguage`), with fallback; the translated templates and strings
are covered by the i18n test suite (see
[10_internationalization](10_internationalization.md)).

## Known limits

- No persistent queue on the application side: if Postfix refuses
  durably, the `ERROR` event is journaled but no automatic retry exists.
