#!/bin/bash

set -e

# Ce script permet de démarrer l'application Pyramid Alirpunkto

# Vérification du mode débogage
if [ "$BUILD_WITH_DEBUG" = "1" ]; then
    echo "Mode débogage activé - outils complémentaires disponibles (vim, net-tools, telnet, dnsutils, etc.)"
else
    echo "Mode débogage désactivé - fonctionnement minimal"
fi

# Vérification si le répertoire de l'application est vide (aucun fichier Pyramid)
APP_DIR="/home/alirpunkto/app"
if [ ! -f "${APP_DIR}/setup.py" ] || [ ! -d "${APP_DIR}/alirpunkto" ]; then
    echo "Le répertoire de l'application semble vide ou incomplet. Clonage du dépôt Git..."
    
    # Sauvegarde de tout fichier .env existant
    if [ -f "${APP_DIR}/.env" ]; then
        cp "${APP_DIR}/.env" /tmp/.env.backup
    fi
    
    # Nettoyage du répertoire (sauf var/ si existant)
    find "${APP_DIR}" -mindepth 1 -maxdepth 1 -not -name "var" -exec rm -rf {} \;
    
    # Clonage du dépôt Git
    git clone https://github.com/michaellaunay/alirpunkto.git /tmp/alirpunkto
    
    # Copie des fichiers du dépôt vers le répertoire de l'application
    cp -a /tmp/alirpunkto/. "${APP_DIR}/"
    rm -rf /tmp/alirpunkto
    
    # Restauration du fichier .env s'il existait
    if [ -f "/tmp/.env.backup" ]; then
        cp /tmp/.env.backup "${APP_DIR}/.env"
        rm /tmp/.env.backup
    fi
    
    echo "Dépôt Git cloné avec succès."
fi

# Vérification de l'existence du répertoire var
if [ ! -d "${APP_DIR}/var" ]; then
    echo "Création du répertoire var et de ses sous-répertoires..."
    mkdir -p "${APP_DIR}/var/log" "${APP_DIR}/var/datas" "${APP_DIR}/var/filestorage" "${APP_DIR}/var/sessions"
    chown -R alirpunkto:alirpunkto "${APP_DIR}/var"
fi

# Vérification des dossiers nécessaires
mkdir -p "${APP_DIR}/var/log" "${APP_DIR}/var/datas" "${APP_DIR}/var/filestorage" "${APP_DIR}/var/sessions"

# Vérification du fichier .env
if [ ! -f "${APP_DIR}/.env" ]; then
    echo "Fichier .env non trouvé, création d'un fichier exemple..."
    if [ -f "${APP_DIR}/.env.example" ]; then
        cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
        echo "Veuillez modifier le fichier .env avec vos paramètres personnalisés."
    else
        echo "ATTENTION: Fichier .env.example non trouvé. Impossible de créer un .env par défaut."
    fi
fi

# Vérification que le fichier de configuration existe
if [ ! -f "$1" ]; then
    echo "Erreur: Le fichier de configuration $1 n'existe pas!"
    echo "Usage: start_pyramid.sh [config.ini]"
    exit 1
fi

# Vérification/création de l'environnement virtuel Python
VENV_DIR="/home/alirpunkto/venv"
if [ ! -d "$VENV_DIR" ] || [ ! -f "${VENV_DIR}/bin/activate" ]; then
    echo "Création d'un nouvel environnement virtuel Python..."
    python3 -m venv "$VENV_DIR"
    source "${VENV_DIR}/bin/activate"
    pip install --upgrade pip setuptools wheel
    
    # Installation du package en mode éditable si setup.py existe
    if [ -f "${APP_DIR}/setup.py" ]; then
        echo "Installation du package alirpunkto..."
        pip install -e "${APP_DIR}/[testing]"
    else
        echo "ATTENTION: setup.py non trouvé. L'installation du package a échoué."
    fi
else
    echo "Utilisation de l'environnement virtuel existant."
    source "${VENV_DIR}/bin/activate"
fi

# Activation de l'environnement virtuel Python
source "${VENV_DIR}/bin/activate"

# Exécution de l'application avec pserve
echo "Démarrage de l'application Alirpunkto avec la configuration: $1"
exec pserve "$@"