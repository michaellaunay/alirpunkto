#!/bin/bash
set -e

# Vérifier si les certificats existent
if [ ! -f "/etc/letsencrypt/live/alirpunkto.com/fullchain.pem" ]; then
    echo "Certificats introuvables pour alirpunkto.com, lancement de certbot en mode standalone pour obtenir les certificats..."
    
    # S'assurer qu'Apache n'est pas déjà démarré sur les ports 80/443
    service apache2 stop || true

    # Lancer Certbot en mode standalone
    certbot certonly --standalone --non-interactive --agree-tos --email admin@alirpunkto.com -d alirpunkto.com
fi

# (Optionnel) Tenter de renouveler silencieusement les certificats
certbot renew --quiet

echo "Démarrage d'Apache2..."
apache2ctl -D FOREGROUND

