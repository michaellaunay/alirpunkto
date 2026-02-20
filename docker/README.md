For security reason, you must place the admin password in the host file secrets/ldap_password, located in the installation base directory.
To manualy create ldap contener do :

```bash
#!/usr/bin/env bash
set -euo pipefail

DEBUG_LDAP=${DEBUG_LDAP:-false}
SECRETS_DIR="docker/secrets"
LDAP_SECRET_FILE="$SECRETS_DIR/ldap_password"

if [[ ! -e "$LDAP_SECRET_FILE" ]]; then
  echo "Please fill $LDAP_SECRET_FILE with the LDAP container password"
  exit 1
fi

# Ensure secrets directory exists with strict permissions
mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

# Copy your .env into the docker directory to customize it, or create a proper link
# Check if docker.env exist
if [[ ! -e docker/.env ]]; then
  cp .env docker/.env
  echo "Copy .env to docker/.env please adapte this copy !"
  wait 5
fi
 
# Load .env file and export variables
set -a
source docker/.env
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

# Update initials_users exemple with LDAP_BASE_DN from .env
# Please change the two initial ldap user
sed "s|dc=alirpunkto,dc=org|${LDAP_BASE_DN}|g" \
  docker/initials_users.ldif > docker/initials_users.generated.ldif

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
  -e DEBUG_LDAP="${DEBUG_LDAP:-false}" \
  -v $(pwd)/alirpunkto/alirpunkto_schema.ldif:/schema/alirpunkto_schema.ldif:ro \
  -v alirpunkto_ldap_etc:/etc/ldap \
  -v alirpunkto_ldap_var:/var/lib/ldap \
  -v $(pwd)/docker/secrets/ldap_password:/run/secrets/ldap_password:ro \
  alirpunkto-ldap
```

If volumes existe you must delete them :
```bash
docker volume rm alirpunkto_ldap_etc
docker volume rm alirpunkto_ldap_var
```
