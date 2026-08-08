#!/bin/bash
set -euo pipefail

DOMAIN="${DOMAIN:-alirpunkto.com}"
POSTFIX_MYHOSTNAME="${POSTFIX_MYHOSTNAME:-${DOMAIN}}"
POSTFIX_RELAYHOST="${POSTFIX_RELAYHOST:-}"
POSTFIX_INET_PROTOCOLS="${POSTFIX_INET_PROTOCOLS:-ipv4}"
POSTFIX_MESSAGE_SIZE_LIMIT="${POSTFIX_MESSAGE_SIZE_LIMIT:-26214400}"
POSTFIX_MYNETWORKS="${POSTFIX_MYNETWORKS:-}"
FAILOVER_IP="${FAILOVER_IP:-}"

cleanup() {
    if [ -n "${POSTFIX_PID:-}" ] && kill -0 "${POSTFIX_PID}" 2>/dev/null; then
        kill "${POSTFIX_PID}" 2>/dev/null || true
        wait "${POSTFIX_PID}" 2>/dev/null || true
    fi

    if [ -n "${OPENDKIM_PID:-}" ] && kill -0 "${OPENDKIM_PID}" 2>/dev/null; then
        kill "${OPENDKIM_PID}" 2>/dev/null || true
        wait "${OPENDKIM_PID}" 2>/dev/null || true
    fi
}

trap cleanup EXIT INT TERM

echo "[Init] Preparing directories"
mkdir -p \
    /etc/dkimkeys \
    /run/opendkim \
    /var/spool/postfix \
    /etc/opendkim

chown root:opendkim /etc/dkimkeys /run/opendkim
chmod 775 /run/opendkim

if [ ! -f "/etc/dkimkeys/dkim.private" ]; then
    echo "[Init] Generating DKIM key for ${DOMAIN}"
    opendkim-genkey -D /etc/dkimkeys -d "${DOMAIN}" -s dkim
fi

chown root:opendkim /etc/dkimkeys/dkim.private
chmod 640 /etc/dkimkeys/dkim.private

cat > /etc/opendkim/KeyTable <<EOF
dkim._domainkey.${DOMAIN} ${DOMAIN}:dkim:/etc/dkimkeys/dkim.private
EOF

cat > /etc/opendkim/SigningTable <<EOF
*@${DOMAIN} dkim._domainkey.${DOMAIN}
EOF

cat > /etc/opendkim/TrustedHosts <<EOF
127.0.0.1
localhost
${DOMAIN}
EOF

echo "[Init] Configuring Postfix"

postconf -e "myhostname = ${POSTFIX_MYHOSTNAME}"
postconf -e "mydomain = ${DOMAIN}"
postconf -e "myorigin = ${DOMAIN}"
postconf -e "mydestination = localhost"

# Test-stack capture mode (POSTFIX_LOCAL_CAPTURE=1, set only by
# docker/test-docker-compose.yaml): deliver every message addressed
# to ${DOMAIN} into the local mailbox of the "catchall" user instead
# of relaying it — the e2e scenarios read the challenge e-mails from
# /var/mail/catchall. Unknown local users all land there too
# (luser_relay with an empty local_recipient_maps).
if [ "${POSTFIX_LOCAL_CAPTURE:-0}" = "1" ]; then
    id catchall >/dev/null 2>&1 || useradd -m catchall
    postconf -e "mydestination = localhost, ${DOMAIN}"
    postconf -e "luser_relay = catchall"
    postconf -e "local_recipient_maps ="
fi
postconf -e "relay_domains = ${DOMAIN}"
postconf -e "inet_interfaces = all"
postconf -e "inet_protocols = ${POSTFIX_INET_PROTOCOLS}"
postconf -e "message_size_limit = ${POSTFIX_MESSAGE_SIZE_LIMIT}"

postconf -e "milter_protocol = 6"
postconf -e "milter_default_action = accept"
postconf -e "smtpd_milters = unix:/run/opendkim/opendkim.sock"
postconf -e "non_smtpd_milters = unix:/run/opendkim/opendkim.sock"

# Relay policy: only trusted networks (mynetworks, see below) may relay;
# everything else is rejected. If you switch to SASL auth, add
# "permit_sasl_authenticated" to each list below.
postconf -e "smtpd_relay_restrictions = permit_mynetworks, reject_unauth_destination"

# Defense in depth: explicit HELO / sender / recipient restrictions.
postconf -e "smtpd_helo_required = yes"
postconf -e "smtpd_helo_restrictions = permit_mynetworks, reject_invalid_helo_hostname, reject_non_fqdn_helo_hostname"
postconf -e "smtpd_sender_restrictions = permit_mynetworks, reject_non_fqdn_sender, reject_unknown_sender_domain"
postconf -e "smtpd_recipient_restrictions = permit_mynetworks, reject_non_fqdn_recipient, reject_unauth_destination"

# Anti-abuse rate limiting (anvil): bounds abuse even if the relay were reachable.
postconf -e "smtpd_client_connection_rate_limit = 30"
postconf -e "smtpd_client_message_rate_limit = 100"
postconf -e "anvil_rate_time_unit = 60s"

postconf -e "smtp_host_lookup = dns"
postconf -e "disable_dns_lookups = no"

if [ -n "${POSTFIX_RELAYHOST}" ]; then
    postconf -e "relayhost = ${POSTFIX_RELAYHOST}"
fi

if [ -n "${FAILOVER_IP}" ]; then
    postconf -e "smtp_bind_address = ${FAILOVER_IP}"
fi

# Networks allowed to relay.
#   - If POSTFIX_MYNETWORKS is set (docker/.env), it wins — use this for an
#     explicit, reviewed perimeter, or when SASL is not enabled and you want a
#     fixed range.
#   - Otherwise auto-detect this container's own bridge subnet. The Compose
#     network already exists when the container starts, so eth0 is in the app
#     subnet and detection is reliable and self-adjusting (no hard-coded IP).
#
# SAFE because port 25 is NOT published (see docker-compose.yaml): with no
# external ingress, trusting the private app subnet cannot become an Internet
# open relay. If you EVER publish port 25 (inbound MX), do NOT rely on this —
# set POSTFIX_MYNETWORKS to a tight range or, better, enable SASL and drop
# permit_mynetworks.
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

# In Docker, Postfix chroot often causes DNS lookup issues.
# Disable smtpd chroot for the SMTP listener.
postconf -M smtp/inet="smtp      inet  n       -       n       -       -       smtpd"

echo "[Init] Preparing Postfix chroot DNS files"

mkdir -p /var/spool/postfix/etc

cp /etc/resolv.conf /var/spool/postfix/etc/resolv.conf
cp /etc/hosts /var/spool/postfix/etc/hosts
cp /etc/services /var/spool/postfix/etc/services 2>/dev/null || true
cp /etc/nsswitch.conf /var/spool/postfix/etc/nsswitch.conf 2>/dev/null || true

chown root:root /var/spool/postfix/etc
chown root:root /var/spool/postfix/etc/resolv.conf /var/spool/postfix/etc/hosts
chmod 755 /var/spool/postfix/etc
chmod 644 /var/spool/postfix/etc/resolv.conf /var/spool/postfix/etc/hosts

echo "[Init] Fixing Postfix spool/chroot permissions"

chown -R root:root /var/spool/postfix/lib /var/spool/postfix/usr 2>/dev/null || true
chmod -R go-w /var/spool/postfix/lib /var/spool/postfix/usr 2>/dev/null || true

postfix set-permissions || true
postfix check || true

start_opendkim() {
    /usr/sbin/opendkim -f -x /etc/opendkim.conf &
    OPENDKIM_PID=$!
    echo "[Init] OpenDKIM started (pid ${OPENDKIM_PID})"
}

start_postfix() {
    postfix start-fg &
    POSTFIX_PID=$!
    echo "[Init] Postfix started (pid ${POSTFIX_PID})"
}

echo "[Init] Starting OpenDKIM"
start_opendkim

echo "[Init] DNS record to publish for DKIM:"
cat /etc/dkimkeys/dkim.txt || true

echo "[Init] Starting Postfix"
start_postfix

# §3 correctif 3 — supervise both children instead of `wait -n`.
# Previously `wait -n` returned as soon as EITHER process exited and the EXIT
# trap then killed the other, so a single transient hiccup of OpenDKIM or
# Postfix tore down the whole mail container. Here we restart whichever child
# dies and keep running; the container stops only on an explicit signal
# (INT/TERM), where the trap performs a clean shutdown.
while true; do
    if ! kill -0 "${OPENDKIM_PID}" 2>/dev/null; then
        echo "[Init][WARN] OpenDKIM exited; restarting" >&2
        start_opendkim
    fi
    if ! kill -0 "${POSTFIX_PID}" 2>/dev/null; then
        echo "[Init][WARN] Postfix exited; restarting" >&2
        start_postfix
    fi
    sleep 5
done
