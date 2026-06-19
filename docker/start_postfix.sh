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
postconf -e "relay_domains = ${DOMAIN}"
postconf -e "inet_interfaces = all"
postconf -e "inet_protocols = ${POSTFIX_INET_PROTOCOLS}"
postconf -e "message_size_limit = ${POSTFIX_MESSAGE_SIZE_LIMIT}"

postconf -e "milter_protocol = 6"
postconf -e "milter_default_action = accept"
postconf -e "smtpd_milters = unix:/run/opendkim/opendkim.sock"
postconf -e "non_smtpd_milters = unix:/run/opendkim/opendkim.sock"

postconf -e "smtpd_relay_restrictions = permit_mynetworks,reject_unauth_destination"
postconf -e "smtp_host_lookup = dns"
postconf -e "disable_dns_lookups = no"

if [ -n "${POSTFIX_RELAYHOST}" ]; then
    postconf -e "relayhost = ${POSTFIX_RELAYHOST}"
fi

if [ -n "${FAILOVER_IP}" ]; then
    postconf -e "smtp_bind_address = ${FAILOVER_IP}"
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

echo "[Init] Starting OpenDKIM"

/usr/sbin/opendkim -f -x /etc/opendkim.conf &
OPENDKIM_PID=$!

echo "[Init] DNS record to publish for DKIM:"
cat /etc/dkimkeys/dkim.txt || true

echo "[Init] Starting Postfix"

postfix start-fg &
POSTFIX_PID=$!

wait -n "${OPENDKIM_PID}" "${POSTFIX_PID}"
