#!/bin/bash
set -euo pipefail

DOMAIN="${DOMAIN:-alirpunkto.com}"
POSTFIX_MYHOSTNAME="${POSTFIX_MYHOSTNAME:-${DOMAIN}}"
POSTFIX_RELAYHOST="${POSTFIX_RELAYHOST:-}"
POSTFIX_INET_PROTOCOLS="${POSTFIX_INET_PROTOCOLS:-ipv4}"
POSTFIX_MESSAGE_SIZE_LIMIT="${POSTFIX_MESSAGE_SIZE_LIMIT:-26214400}"
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

mkdir -p /etc/dkimkeys /run/opendkim /var/spool/postfix
chown root:opendkim /etc/dkimkeys /run/opendkim
chmod 775 /run/opendkim

if [ -d "/var/spool/postfix" ]; then
    chown -R postfix:postfix /var/spool/postfix
    chmod 750 /var/spool/postfix
fi

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

postconf -e "myhostname = ${POSTFIX_MYHOSTNAME}"
postconf -e "mydomain = ${DOMAIN}"
postconf -e "myorigin = ${DOMAIN}"
postconf -e "mydestination = localhost"
postconf -e "relay_domains = ${DOMAIN}"
postconf -e "inet_interfaces = all"
postconf -e "inet_protocols = ${POSTFIX_INET_PROTOCOLS}"
postconf -e "message_size_limit = ${POSTFIX_MESSAGE_SIZE_LIMIT}"
postconf -e "milter_protocol = 6"
postconf -e "milter_default_action = accept"
postconf -e "smtpd_milters = unix:/run/opendkim/opendkim.sock"
postconf -e "non_smtpd_milters = unix:/run/opendkim/opendkim.sock"
postconf -e 'smtpd_relay_restrictions = permit_mynetworks,reject_unauth_destination'

if [ -n "${POSTFIX_RELAYHOST}" ]; then
    postconf -e "relayhost = ${POSTFIX_RELAYHOST}"
fi

if [ -n "${FAILOVER_IP}" ]; then
    postconf -e "smtp_bind_address = ${FAILOVER_IP}"
fi

SUBNET="$(ip -o -f inet addr show eth0 | awk '/scope global/ {print $4}' | head -n1 || true)"
if [ -n "${SUBNET}" ]; then
    postconf -e "mynetworks = 127.0.0.0/8 ${SUBNET}"
else
    postconf -e "mynetworks = 127.0.0.0/8"
fi

echo "[Init] Starting OpenDKIM"
/usr/sbin/opendkim -f -x /etc/opendkim.conf &
OPENDKIM_PID=$!

echo "[Init] DNS record to publish for DKIM:"
cat /etc/dkimkeys/dkim.txt

echo "[Init] Starting Postfix"
postfix start-fg &
POSTFIX_PID=$!

wait -n "${OPENDKIM_PID}" "${POSTFIX_PID}"
