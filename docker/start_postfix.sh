#!/bin/bash
set -e

#############################
# Fixe les permissions si nécessaire
#############################
# 1. Corriger les permissions du spool Postfix si le répertoire est monté
if [ -d "/var/spool/postfix" ] ; then
  chown -R postfix:postfix /var/spool/postfix
  chmod -R 750 /var/spool/postfix
fi
# 2. Corriger les permissions de la clé DKIM privée, si elle existe
if [ -f "/etc/dkimkeys/dkim.private" ] ; then
  chown root:opendkim /etc/dkimkeys/dkim.private
  chmod 660 /etc/dkimkeys/dkim.private
fi
# 3. Corriger les permissions du fichier de log des mails
if [ -f "/var/log/mail.log" ] ; then
  chown postfix:root /var/log/mail.log
fi

#############################
# Utilisation de l'adresse ipfailover
#############################
if [ -n "$FAILOVER_IP" ]; then
    echo "[Init] Paramétrage de l'IP de FailOver : $FAILOVER_IP"
    if grep -q "^smtp_bind_address" /etc/postfix/main.cf; then
        sed -i "s/^smtp_bind_address.*/smtp_bind_address = $FAILOVER_IP/" /etc/postfix/main.cf
    else
        echo "smtp_bind_address = $FAILOVER_IP" >> /etc/postfix/main.cf
    fi
fi

#############################
# Mise à jour de Postfix
#############################

# Extraction du CIDR associé à l’interface eth0
# On filtre sur "scope global" pour éviter les adresses de loopback, link local...
# On suppose ici qu'il n'y a qu'une seule IP / interface ou qu’on veut la première occurrence
SUBNET=$(ip -o -f inet addr show eth0 | awk '/scope global/ {print $4}' | head -n1)

echo "Détection du réseau Docker : $SUBNET"

# Retirer la ligne "mynetworks" si elle existe déjà
sed -i '/^mynetworks /d' /etc/postfix/main.cf

# Réécrire une ligne mynetworks (127.0.0.0/8 et le SUBNET détecté)
# Vous pouvez ajouter d'autres sous-réseaux ou ne pas retirer la ligne précédente si vous préférez cumuler.
echo "mynetworks = 127.0.0.0/8, $SUBNET" >> /etc/postfix/main.cf

echo "Mise à jour de la directive mynetworks, contenu actuel :"
grep -E '^mynetworks' /etc/postfix/main.cf || true

#############################
# Génération automatique de la clé DKIM
#############################
if [ -n "$DOMAIN" ]; then
  if [ ! -f "/etc/dkimkeys/dkim.private" ]; then
    echo "[Init] Génération de la paire DKIM pour le domaine $DOMAIN"
    mkdir -p /etc/dkimkeys
    cd /etc/dkimkeys
    # L'option -t active le mode test (vous pouvez retirer -t en production une fois validé)
    opendkim-genkey -D . -d "$DOMAIN" -s dkim -t
    chown root:opendkim dkim.private
    chmod 660 dkim.private
    echo "=> La clé DKIM a été générée. Voici le contenu du fichier dkim.txt à publier en TXT dans votre zone DNS :"
    cat dkim.txt
    echo ""
  else
    echo "[Init] Clé DKIM déjà présente, pas de génération."
  fi
else
  echo "[Init] Variable DOMAIN non définie, aucune clé DKIM générée."
fi

#############################
# Démarrage d'OpenDKIM
#############################
echo "[Init] Démarrage d'OpenDKIM..."
/usr/sbin/opendkim -x /etc/opendkim.conf &

#############################
# Router localement le port 9025 vers 25
#############################
socat TCP-LISTEN:9025,fork TCP:localhost:25 &

#############################
# Démarrage de Postfix
#############################
echo "[Init] Démarrage de Postfix..."
# Démarrage en arrière-plan de Postfix
postfix start

#############################
# Maintenir le conteneur actif en affichant les logs Postfix
#############################
echo "[Init] Affichage des logs Postfix (Ctrl-C pour quitter)..."
tail -F /var/log/mail.log
