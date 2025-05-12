#!/bin/bash

set -e

# This script starts the Pyramid Alirpunkto application

# Check debug mode
if [ "$BUILD_WITH_DEBUG" = "1" ]; then
    echo "Debug mode enabled - additional tools available (vim, net-tools, telnet, dnsutils, etc.)"
else
    echo "Debug mode disabled - minimal functionality"
fi

# Check if the application directory is empty (no Pyramid files)
APP_DIR="/home/alirpunkto/app"
if [ ! -f "${APP_DIR}/setup.py" ] || [ ! -d "${APP_DIR}/alirpunkto" ]; then
    echo "The application directory appears empty or incomplete. Cloning Git repository..."
    
    # Backup any existing .env file
    if [ -f "${APP_DIR}/.env" ]; then
        cp "${APP_DIR}/.env" /tmp/.env.backup
    fi
    
    # Clean the directory (except var/ if it exists)
    find "${APP_DIR}" -mindepth 1 -maxdepth 1 -not -name "var" -exec rm -rf {} \;
    
    # Clone the Git repository
    git clone https://github.com/michaellaunay/alirpunkto.git /tmp/alirpunkto
    
    # Copy the repository files to the application directory
    cp -a /tmp/alirpunkto/. "${APP_DIR}/"
    rm -rf /tmp/alirpunkto
    
    # Restore the .env file if it existed
    if [ -f "/tmp/.env.backup" ]; then
        cp /tmp/.env.backup "${APP_DIR}/.env"
        rm /tmp/.env.backup
    fi
    
    echo "Git repository cloned successfully."
fi

# Check for the existence of the var directory
if [ ! -d "${APP_DIR}/var" ]; then
    echo "Creating var directory and its subdirectories..."
    mkdir -p "${APP_DIR}/var/log" "${APP_DIR}/var/datas" "${APP_DIR}/var/filestorage" "${APP_DIR}/var/sessions"
    chown -R alirpunkto:alirpunkto "${APP_DIR}/var"
fi

# Check for necessary folders
mkdir -p "${APP_DIR}/var/log" "${APP_DIR}/var/datas" "${APP_DIR}/var/filestorage" "${APP_DIR}/var/sessions"

# Check for .env file
if [ ! -f "${APP_DIR}/.env" ]; then
    echo ".env file not found, creating an example file..."
    if [ -f "${APP_DIR}/.env.example" ]; then
        cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
        echo "Please modify the .env file with your custom parameters."
    else
        echo "WARNING: .env.example file not found. Unable to create a default .env."
    fi
fi

# Check if the configuration file exists
if [ ! -f "$1" ]; then
    echo "Error: Configuration file $1 doesn't exist!"
    echo "Usage: start_pyramid.sh [config.ini]"
    exit 1
fi

# Check/create Python virtual environment
VENV_DIR="/home/alirpunkto/venv"
if [ ! -d "$VENV_DIR" ] || [ ! -f "${VENV_DIR}/bin/activate" ]; then
    echo "Creating a new Python virtual environment..."
    python3 -m venv "$VENV_DIR"
    source "${VENV_DIR}/bin/activate"
    pip install --upgrade pip setuptools wheel
    
    # Install the package in editable mode if setup.py exists
    if [ -f "${APP_DIR}/setup.py" ]; then
        echo "Installing the alirpunkto package..."
        pip install -e "${APP_DIR}/[testing]"
    else
        echo "WARNING: setup.py not found. Package installation failed."
    fi
else
    echo "Using existing virtual environment."
    source "${VENV_DIR}/bin/activate"
fi

# Activate Python virtual environment
source "${VENV_DIR}/bin/activate"

# Run the application with pserve
echo "Starting the Alirpunkto application with configuration: $1"
exec pserve "$@"