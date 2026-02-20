#!/bin/bash
set -e

echo "docker stop alirpunkto-ldap"
docker stop alirpunkto-ldap || true
echo "docker rm alirpunkto-ldap"
docker rm alirpunkto-ldap  || true
echo "docker image rm alirpunkto-ldap:latest"
docker image rm alirpunkto-ldap:latest || true
echo "docker volume rm alirpunkto_ldap_etc"
docker volume rm alirpunkto_ldap_etc || true
echo "docker volume rm alirpunkto_ldap_var"
docker volume rm alirpunkto_ldap_var || true
echo "remove docker/var/*"

echo "Cleanup finished."

