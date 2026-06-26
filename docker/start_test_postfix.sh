#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${DOMAIN:-alirpunkto.localhost}"
POSTFIX_MYHOSTNAME="${POSTFIX_MYHOSTNAME:-mail.${DOMAIN}}"
POSTFIX_INET_PROTOCOLS="${POSTFIX_INET_PROTOCOLS:-ipv4}"
POSTFIX_MESSAGE_SIZE_LIMIT="${POSTFIX_MESSAGE_SIZE_LIMIT:-26214400}"
POSTFIX_MYNETWORKS="${POSTFIX_MYNETWORKS:-}"
POSTFIX_DISABLE_EXTERNAL_DELIVERY="${POSTFIX_DISABLE_EXTERNAL_DELIVERY:-true}"

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

echo "[Postfix:test] Preparing directories"
mkdir -p /etc/dkimkeys /run/opendkim /var/spool/postfix /etc/opendkim
chown root:opendkim /etc/dkimkeys /run/opendkim
chmod 775 /run/opendkim

if [ ! -f "/etc/dkimkeys/dkim.private" ]; then
    echo "[Postfix:test] Generating local DKIM key for ${DOMAIN}"
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
${POSTFIX_MYHOSTNAME}
EOF

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
postconf -e "milter_protocol = 6"
postconf -e "milter_default_action = accept"
postconf -e "smtpd_milters = unix:/run/opendkim/opendkim.sock"
postconf -e "non_smtpd_milters = unix:/run/opendkim/opendkim.sock"

# Offline mode: do not perform DNS lookups and never relay outside the test stack.
postconf -e "smtp_host_lookup = native"
postconf -e "disable_dns_lookups = yes"
postconf -e "ignore_mx_lookup_error = yes"

if [ "${POSTFIX_DISABLE_EXTERNAL_DELIVERY}" = "true" ]; then
    # Accept messages from Pyramid, then discard them locally.
    # This validates the SMTP path without sending anything to the Internet.
    postconf -M "discard/unix=discard   unix  -       -       n       -       -       discard"
    postconf -e "default_transport = discard:"
    postconf -e "relay_transport = discard:"
    postconf -e "local_transport = discard:"
fi

if [ -n "${POSTFIX_MYNETWORKS}" ]; then
    postconf -e "mynetworks = ${POSTFIX_MYNETWORKS}"
else
    NETWORK="$(ip -o -f inet route show dev eth0 | awk '$1 != "default" {print $1; exit}' || true)"
    if [ -n "${NETWORK}" ]; then
        postconf -e "mynetworks = 127.0.0.0/8 ${NETWORK}"
    else
        postconf -e "mynetworks = 127.0.0.0/8"
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

echo "[Postfix:test] Starting OpenDKIM"
/usr/sbin/opendkim -f -x /etc/opendkim.conf &
OPENDKIM_PID=$!

echo "[Postfix:test] Local DKIM record, not to publish publicly:"
cat /etc/dkimkeys/dkim.txt || true

echo "[Postfix:test] Starting Postfix in offline sink mode"
postfix start-fg &
POSTFIX_PID=$!

wait -n "${OPENDKIM_PID}" "${POSTFIX_PID}"
