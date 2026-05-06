# Docker Images

This directory contains the Dockerfiles, startup scripts, and the Compose stack
for the main Alirpunkto services:

- `DockerfileOpenLDAP`
- `DockerfilePyramid`
- `DockerfileApache2`
- `DockerfilePostfix`

> **All commands are run from the repository root**, not from inside `docker/`.

---

## Quick start (recommended)

### 1. Run the initialiser

```bash
chmod +x docker/init.sh
./docker/init.sh
```

The script asks for:

- domain name and maintainer e-mail
- LDAP admin password and login DN prefix
- application admin account (login, e-mail, password, pseudonym, and `LDAP_ADMIN_OID` — the UUID
  used by Pyramid to identify the admin entry in LDAP; defaults to a generated UUID,
  **do not leave the all-zero placeholder in production**)
- first and second bootstrap users (name, e-mail, language, nationality, role, pseudonym)
- Apache / Let's Encrypt settings
- Postfix relay host (optional)
- LDAP server hostname and port as seen by the Pyramid container
- Keycloak / SSO settings (optional)

It generates:

| File | Description |
|---|---|
| `docker/.env` | All runtime variables consumed by Compose (includes `LDAP_ADMIN_OID`) |
| `docker/secrets/ldap_password` | LDAP password file (mode 600, **never commit**) |
| `docker/initials_users.generated.ldif` | Bootstrap users with hashed passwords (admin + 2 users) |

> **Security note:** passwords are hashed with `slappasswd` ({SSHA}).
> The script warns if `slappasswd` is not installed (`apt install slapd`).
>
> **`LDAP_ADMIN_OID`** is the UUID stored as `uid` in the LDAP admin entry and
> read by Pyramid via `constants_and_globals.py`. It must match between the
> generated LDIF and the `.env` file — `init.sh` guarantees this automatically.
>
> **Pseudonym** is the login identifier typed in the web interface. It is stored
> as the LDAP `cn` attribute and must be 5–20 ASCII characters (`[a-zA-Z0-9_.-]`).
> Names with accents (e.g. `Michaël`) cannot be used as-is — choose an ASCII
> pseudonym such as `michael.launay` or `mlaunay` instead.

### 2. Start the stack

```bash
docker compose --env-file docker/.env -f docker/docker-compose.yaml up -d
```

Compose starts services in dependency order using healthchecks:

1. `alirpunkto-ldap` + `alirpunkto-postfix` (in parallel)
2. `alirpunkto-pyramid` (waits for both)
3. `alirpunkto-apache2` (waits for Pyramid)

The `alirpunkto-net` network is created automatically.

### 3. Reset and reinitialise

```bash
docker compose --env-file docker/.env -f docker/docker-compose.yaml down
docker volume rm alirpunkto_ldap_etc alirpunkto_ldap_var
./docker/init.sh
docker compose --env-file docker/.env -f docker/docker-compose.yaml up -d
```

> If you also want to wipe the Pyramid object database (ZODB):
> ```bash
> docker volume rm alirpunkto_pyramid_var
> ```

---

## Debug builds

Both `DockerfileOpenLDAP` and `DockerfilePyramid` accept `BUILD_WITH_DEBUG=1`
to add tools like `vim`, `ldapvi`, `dnsutils`, and `iputils-ping`:

```bash
# OpenLDAP debug image
docker buildx build \
  --build-arg BUILD_WITH_DEBUG=1 \
  -f docker/DockerfileOpenLDAP \
  -t alirpunkto-ldap:debug .

# Pyramid debug image
docker build \
  --build-arg BUILD_WITH_DEBUG=1 \
  -f docker/DockerfilePyramid \
  -t alirpunkto-pyramid:debug .
```

You can also set `BUILD_WITH_DEBUG=1` in `docker/.env` so that
`docker compose build` picks it up automatically.

---

## Manual operation (without Compose)

Useful for troubleshooting or rebuilding a single service. Source the env file
first:

```bash
set -a && source docker/.env && set +a
```

### OpenLDAP

```bash
# Build (context = repo root)
docker buildx build -f docker/DockerfileOpenLDAP -t alirpunkto-ldap .

# Create volumes
docker volume create alirpunkto_ldap_etc
docker volume create alirpunkto_ldap_var

# Run
docker run --name alirpunkto-ldap \
  --network alirpunkto-net \
  -p 8389:389 \
  -p 8636:636 \
  -e LDAP_BASE_DN="$LDAP_BASE_DN" \
  -e LDAP_ORGANIZATION="$LDAP_ORGANIZATION" \
  -e LDAP_PASSWORD_FILE=/run/secrets/ldap_password \
  -e INITIAL_USERS_LDIF=/initials_users.generated.ldif \
  -v "$(pwd)/alirpunkto/alirpunkto_schema.ldif:/schema/alirpunkto_schema.ldif:ro" \
  -v "$(pwd)/docker/initials_users.generated.ldif:/initials_users.generated.ldif:ro" \
  -v alirpunkto_ldap_etc:/etc/ldap \
  -v alirpunkto_ldap_var:/var/lib/ldap \
  -v "$(pwd)/docker/secrets/ldap_password:/run/secrets/ldap_password:ro" \
  alirpunkto-ldap

# Clean reinitialization
docker rm -f alirpunkto-ldap
docker volume rm alirpunkto_ldap_etc alirpunkto_ldap_var
```

### Pyramid

`DockerfilePyramid` copies the whole project — build context must be the repo root.

```bash
docker build -f docker/DockerfilePyramid -t alirpunkto-pyramid .

docker volume create alirpunkto_pyramid_var

docker run --name alirpunkto-pyramid \
  --network alirpunkto-net \
  -p 6543:6543 \
  -e LDAP_SERVER=alirpunkto-ldap \
  -e LDAP_PORT=389 \
  -e MAIL_HOST=alirpunkto-postfix \
  -v alirpunkto_pyramid_var:/home/alirpunkto/app/var \
  -v "$(pwd)/docker/.env:/home/alirpunkto/app/.env:ro" \
  alirpunkto-pyramid
```

Override the config file if needed:

```bash
docker run --rm alirpunkto-pyramid development.ini
```

### Apache2

```bash
docker build -f docker/DockerfileApache2 -t alirpunkto-apache2 .

docker volume create alirpunkto_apache_letsencrypt
docker volume create alirpunkto_apache_letsencrypt_lib

docker run --name alirpunkto-apache2 \
  --network alirpunkto-net \
  -p 8080:80 \
  -p 8443:443 \
  -e APACHE_SERVER_NAME="$APACHE_SERVER_NAME" \
  -e APACHE_BACKEND_HOST=alirpunkto-pyramid \
  -e APACHE_BACKEND_PORT=6543 \
  -e ENABLE_CERTBOT=false \
  -v alirpunkto_apache_letsencrypt:/etc/letsencrypt \
  -v alirpunkto_apache_letsencrypt_lib:/var/lib/letsencrypt \
  alirpunkto-apache2
```

To request a TLS certificate automatically:

```bash
  -e ENABLE_CERTBOT=true \
  -e LETSENCRYPT_EMAIL="$LETSENCRYPT_EMAIL"
```

### Postfix

```bash
docker build -f docker/DockerfilePostfix -t alirpunkto-postfix .

docker volume create alirpunkto_postfix_spool
docker volume create alirpunkto_postfix_dkim

docker run --name alirpunkto-postfix \
  --network alirpunkto-net \
  -p 9025:25 \
  -e DOMAIN="$DOMAIN" \
  -e POSTFIX_MYHOSTNAME="$POSTFIX_MYHOSTNAME" \
  -v alirpunkto_postfix_spool:/var/spool/postfix \
  -v alirpunkto_postfix_dkim:/etc/dkimkeys \
  alirpunkto-postfix
```

Optional variables: `POSTFIX_RELAYHOST`, `POSTFIX_INET_PROTOCOLS`,
`POSTFIX_MESSAGE_SIZE_LIMIT`, `FAILOVER_IP`.

On first start, retrieve the DKIM DNS record with:

```bash
docker logs alirpunkto-postfix | grep -A 10 "DNS record to publish"
```

Create a DNS TXT record for `dkim._domainkey.<your-domain>` with the `p=` value
shown (concatenate the quoted strings, strip parentheses and quotes).

---

## Inspecting a running container

```bash
# Open a shell in any container
docker exec -it alirpunkto-ldap bash
docker exec -it alirpunkto-pyramid bash
docker exec -it alirpunkto-postfix bash
docker exec -it alirpunkto-apache2 bash
```

### Query LDAP from inside the LDAP container

```bash
ldapsearch -x \
  -H ldap://localhost \
  -D "cn=admin,$LDAP_BASE_DN" \
  -w "$LDAP_PASSWORD" \
  -b "$LDAP_BASE_DN" \
  "(objectClass=inetOrgPerson)"
```

### Python REPL with the full Pyramid environment

```bash
docker exec -it alirpunkto-pyramid bash
source /home/alirpunkto/venv/bin/activate
cd /home/alirpunkto/app
pshell production.ini   # loads the app; registry, request and root are available
```

Or query LDAP directly with `ldap3`:

```python
from ldap3 import Server, Connection, ALL, SUBTREE
server = Server('ldap://alirpunkto-ldap', get_info=ALL)
conn = Connection(server,
    user='cn=admin,dc=example,dc=com',
    password='secret', auto_bind=True)
conn.search('dc=example,dc=com', '(objectClass=inetOrgPerson)',
    attributes=['cn', 'mail', 'employeeType'])
for e in conn.entries:
    print(e)
conn.unbind()
```

> Use **tmux** on the host before running `docker exec` so that an SSH
> disconnection does not kill your session:
> ```bash
> tmux new -s debug
> docker exec -it alirpunkto-pyramid bash
> # reconnect later with: tmux attach -t debug
> ```

---

## Logs

```bash
# Individual containers
docker logs -f alirpunkto-ldap
docker logs -f alirpunkto-postfix
docker logs -f alirpunkto-pyramid
docker logs -f alirpunkto-apache2

# Full stack via Compose
docker compose --env-file docker/.env -f docker/docker-compose.yaml logs -f
```
