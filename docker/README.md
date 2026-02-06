For security reason, you must place the admin password in the host file secrets/ldap_password, located in the installation base directory.
To manualy create ldap contener do :

```bash
#!/usr/bin/env bash
set -euo pipefail

SECRETS_DIR="secrets"
LDAP_SECRET_FILE="$SECRETS_DIR/ldap_password"

# Ensure secrets directory exists with strict permissions
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

# Load .env file and export variables
set -a
source .env
set +a

# Copy LDAP_PASSWORD into a secret file
if [[ -z "${LDAP_PASSWORD:-}" ]]; then
  echo "[ERROR] LDAP_PASSWORD is not set in .env"
  exit 1
fi

# Ensure the secret file is created with restrictive permissions
umask 077
printf '%s' "$LDAP_PASSWORD" > "$LDAP_SECRET_FILE"

# Remove sensitive variables from the environment
while IFS='=' read -r var _; do
  case "$var" in
    *SECRET*|*PWD*|*PASSWORD*)
      unset "$var"
      ;;
  esac
done < <(env)

# Create the docker image for ldap service
docker buildx build -f docker/DockerfileOpenLDAP  -t alirpunkto-ldap docker

docker volume create alirpunkto_ldap_etc
docker volume create alirpunkto_ldap_var
# Run the Docker container
docker run --name alirpunkto-ldap \
  -p 8389:389 -p 8636:636 \
  -e LDAP_BASE_DN="$LDAP_BASE_DN" \
  -e LDAP_ORGANIZATION="$LDAP_ORGANIZATION" \
  -e LDAP_PASSWORD_FILE=/run/secrets/ldap_password \
  -v $(pwd)/alirpunkto/alirpunkto_schema.ldif:/alirpunkto_schema.ldif \
  -v alirpunkto_ldap_etc:/etc/ldap \
  -v alirpunkto_ldap_var:/var/lib/ldap \
  -v $(pwd)/secrets/ldap_password:/run/secrets/ldap_password:ro \
  alirpunkto-ldap
```

If volumes existe you must delete them :
```bash
docker volume rm alirpunkto_ldap_etc
docker volume rm alirpunkto_ldap_var
```