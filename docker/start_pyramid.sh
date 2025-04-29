#!/bin/bash
set -e

# Se déplacer dans le répertoire datas
cd datas

# Lancer pserve
exec bin/pserve production.ini

