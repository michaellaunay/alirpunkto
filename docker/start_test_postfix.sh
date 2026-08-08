#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${DOMAIN:-alirpunkto.localhost}"
POSTFIX_MYHOSTNAME="${POSTFIX_MYHOSTNAME:-mail.${DOMAIN}}"
POSTFIX_INET_PROTOCOLS="${POSTFIX_INET_PROTOCOLS:-ipv4}"
POSTFIX_MESSAGE_SIZE_LIMIT="${POSTFIX_MESSAGE_SIZE_LIMIT:-26214400}"
POSTFIX_MYNETWORKS="${POSTFIX_MYNETWORKS:-}"
POSTFIX_DISABLE_EXTERNAL_DELIVERY="${POSTFIX_DISABLE_EXTERNAL_DELIVERY:-true}"

# §3 correctif 4 — this sink accepts messages and discards them, so it does NOT
# sign DKIM. OpenDKIM and the milter wiring have been removed: they added a
# second long-running process that, combined with `wait -n`, could take the
# whole container down for nothing. Postfix now runs as PID 1 (see `exec`
# below), so there is no two-process supervision to get wrong.

echo "[Postfix:test] Preparing directories"
mkdir -p /var/spool/postfix

echo "[Postfix:test] Configuring local SMTP sink"

postconf -e "myhostname = ${POSTFIX_MYHOSTNAME}"
postconf -e "mydomain = ${DOMAIN}"
postconf -e "myorigin = ${DOMAIN}"
postconf -e "mydestination = localhost localhost.localdomain ${DOMAIN} ${POSTFIX_MYHOSTNAME}"
postconf -e "relay_domains ="
postconf -e "relayhost ="
postconf -e "inet_interfaces = all"
postconf -e "inet_protocols = ${POSTFIX_INET_PROTOCOLS}"
postconf -e "message_size_limit = ${POSTFIX_MESSAGE_SIZE_LIMIT}"
postconf -e "smtpd_relay_restrictions = permit_mynetworks,reject_unauth_destination"

# No milters: the sink does not sign or filter, it only accepts and discards.
postconf -X "smtpd_milters" 2>/dev/null || true
postconf -X "non_smtpd_milters" 2>/dev/null || true

# Offline mode: do not perform DNS lookups and never relay outside the test stack.
postconf -e "smtp_host_lookup = native"
postconf -e "disable_dns_lookups = yes"
postconf -e "ignore_mx_lookup_error = yes"

# Mail log on stdout so `docker logs` shows deliveries (postfix >= 3.4).
postconf -e "maillog_file = /dev/stdout"

if [ "${POSTFIX_LOCAL_CAPTURE:-0}" = "1" ]; then
    # Capture mode (set by docker/test-docker-compose.yaml): KEEP the
    # test domain's mail in the local catchall mailbox — the e2e
    # scenarios read the challenge e-mails from /var/mail/catchall —
    # while everything addressed outside the stack is still
    # discarded. Local recipients all resolve to catchall
    # (luser_relay with an empty local_recipient_maps).
    id catchall >/dev/null 2>&1 || useradd -m catchall
    postconf -M "discard/unix=discard   unix  -       -       n       -       -       discard"
    postconf -e "default_transport = discard:"
    postconf -e "relay_transport = discard:"
    postconf -e "luser_relay = catchall"
    postconf -e "local_recipient_maps ="
elif [ "${POSTFIX_DISABLE_EXTERNAL_DELIVERY}" = "true" ]; then
    # Accept messages from Pyramid, then discard them locally.
    # This validates the SMTP path without sending anything to the Internet.
    postconf -M "discard/unix=discard   unix  -       -       n       -       -       discard"
    postconf -e "default_transport = discard:"
    postconf -e "relay_transport = discard:"
    postconf -e "local_transport = discard:"
fi

# Auto-detect this container's own bridge subnet (self-adjusting, no hard-coded
# IP). The test stack binds port 25 to 127.0.0.1 only, so there is no external
# ingress; POSTFIX_MYNETWORKS may still override for an explicit perimeter.
if [ -n "${POSTFIX_MYNETWORKS}" ]; then
    postconf -e "mynetworks = ${POSTFIX_MYNETWORKS}"
else
    NETWORK="$(ip -o -f inet route show dev eth0 | awk '$1 != "default" {print $1; exit}' || true)"
    if [ -n "${NETWORK}" ]; then
        postconf -e "mynetworks = 127.0.0.0/8 [::1]/128 ${NETWORK}"
    else
        postconf -e "mynetworks = 127.0.0.0/8 [::1]/128"
    fi
fi

# In Docker, Postfix chroot often causes DNS lookup issues. Keep the SMTP listener non-chrooted.
postconf -M smtp/inet="smtp      inet  n       -       n       -       -       smtpd"

mkdir -p /var/spool/postfix/etc
cp /etc/hosts /var/spool/postfix/etc/hosts
cp /etc/services /var/spool/postfix/etc/services 2>/dev/null || true
cp /etc/nsswitch.conf /var/spool/postfix/etc/nsswitch.conf 2>/dev/null || true
printf 'nameserver 127.0.0.1\n' > /var/spool/postfix/etc/resolv.conf

chown root:root /var/spool/postfix/etc /var/spool/postfix/etc/*
chmod 755 /var/spool/postfix/etc
chmod 644 /var/spool/postfix/etc/*

chown -R root:root /var/spool/postfix/lib /var/spool/postfix/usr 2>/dev/null || true
chmod -R go-w /var/spool/postfix/lib /var/spool/postfix/usr 2>/dev/null || true

postfix set-permissions || true
postfix check || true

# §3 correctif 3/4 — run Postfix as PID 1. No background process, no `wait -n`,
# no trap that could tear the container down when a secondary process exits.
# Docker's restart policy handles the rare case where Postfix itself dies.
echo "[Postfix:test] Starting Postfix in offline sink mode (no OpenDKIM)"
exec postfix start-fg
