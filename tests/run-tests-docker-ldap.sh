#!/bin/bash
set -e

# Script pour exécuter les tests avec le conteneur Docker LDAP
# Ce script peut être utilisé en CI/CD ou en local

# Variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="docker-compose.test.yml"
LDAP_PORT=3389
WAIT_TIME=30  # Secondes à attendre pour que le conteneur soit prêt

# Définir la fonction de nettoyage
cleanup() {
    echo "Nettoyage de l'environnement..."
    docker-compose -f "$COMPOSE_FILE" down
    echo "Conteneur LDAP arrêté."
}

# Enregistrer la fonction de nettoyage pour qu'elle soit appelée à la sortie
trap cleanup EXIT

# Vérifier si docker-compose.test.yml existe
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "ERROR: Le fichier $COMPOSE_FILE n'existe pas!"
    echo "Veuillez créer ce fichier en utilisant le modèle fourni."
    exit 1
fi

# Vérifier si le schéma Alirpunkto existe
if [ ! -d "schema" ] || [ ! -f "schema/alirpunkto_schema.ldif" ]; then
    echo "Création du répertoire schema..."
    mkdir -p schema
    
    echo "Copie du schéma alirpunkto_schema.ldif..."
    cp alirpunkto/alirpunkto_schema.ldif schema/
    
    if [ ! -f "schema/alirpunkto_schema.ldif" ]; then
        echo "ERREUR: Impossible de trouver ou de copier le fichier alirpunkto_schema.ldif!"
        exit 1
    fi
fi

# Vérifier si le répertoire test-data existe, sinon le créer
if [ ! -d "test-data" ]; then
    echo "Création du répertoire test-data..."
    mkdir -p test-data
fi

# Démarrer le conteneur LDAP
echo "Démarrage du conteneur LDAP de test..."
docker-compose -f "$COMPOSE_FILE" up -d

# Attendre que le conteneur soit prêt
echo "Attente du démarrage complet du serveur LDAP..."
COUNTER=0
while ! nc -z localhost $LDAP_PORT 2>/dev/null; do
    if [ $COUNTER -ge $WAIT_TIME ]; then
        echo "ERREUR: Le serveur LDAP n'a pas démarré dans le temps imparti!"
        exit 1
    fi
    echo "Attente du serveur LDAP... tentative $COUNTER/$WAIT_TIME"
    sleep 1
    COUNTER=$((COUNTER+1))
done

# Attendre un peu plus pour que LDAP soit complètement initialisé
sleep 5
echo "Le serveur LDAP est opérationnel!"

# Exécuter les tests avec l'option --use-docker-ldap
echo "Exécution des tests avec le conteneur LDAP..."
export USE_DOCKER_LDAP=true
export DOCKER_LDAP_PORT=$LDAP_PORT

# Récupérer le mot de passe admin (si défini dans docker-compose.test.yml)
ADMIN_PASSWORD=$(docker-compose -f "$COMPOSE_FILE" config | grep LDAP_ADMIN_PASSWORD | awk '{print $2}')
if [ -n "$ADMIN_PASSWORD" ]; then
    export LDAP_ADMIN_PASSWORD="$ADMIN_PASSWORD"
    echo "Mot de passe admin LDAP défini: $ADMIN_PASSWORD"
else
    export LDAP_ADMIN_PASSWORD="test_password"
    echo "Utilisation du mot de passe admin LDAP par défaut: test_password"
fi

# Exécuter les tests avec pytest
python -m pytest tests/ --use-docker-ldap -v $@

# Le nettoyage sera effectué automatiquement grâce à la fonction trap cleanup EXIT
echo "Tests terminés avec succès."
