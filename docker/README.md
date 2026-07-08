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

Two networks are created automatically (**R6 — tier segmentation**):
`alirpunkto-frontend` (Apache ↔ Pyramid) and `alirpunkto-backend`
(Pyramid ↔ LDAP/Postfix). Apache cannot reach LDAP or Postfix, and vice-versa,
which limits lateral movement if a public-facing service is compromised.

Internal services are published on **loopback only** (**S3**): `127.0.0.1:8389`/`8636` for LDAP and `127.0.0.1:6543` for Waitress, so the
member directory and the TLS-less backend are never exposed on the host's
external interfaces. Only Apache (`80`/`443`) is public; reach a loopback-bound
service from another host through an SSH tunnel.

Each service ships with **resource limits** and **log rotation** (see
`docker-compose.yaml`):

- **Memory limits** (`mem_limit`) cap each container so a runaway process is
  OOM-killed on its own (and restarted) instead of exhausting host RAM and
  taking the whole stack down. Defaults: 1 GB per service, 8 GB for Pyramid
  (the main workload). Tune to the host with `docker stats`.
- **Log rotation** (`logging: json-file`, `max-size: 10m`, `max-file: 5`) caps
  on-disk logs at ~50 MB per container, so an unbounded log cannot fill the
  host disk.
- **Hardening** (**S5**): every service sets
  `security_opt: no-new-privileges:true` (blocks privilege escalation via
  setuid/setgid binaries). The non-root Pyramid service also drops all Linux
  capabilities (`cap_drop: ALL`). LDAP, Postfix and Apache ship a *commented*
  `cap_drop`/`cap_add` block in `docker-compose.yaml`; enable it after checking
  the service still starts on your host (an over-tight capability set can
  prevent startup).

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

> The helper `docker/stop_clean_delete.sh` tears down the **whole** stack via
> `docker compose down` (the previous version only removed LDAP). Pass
> `--volumes` to also delete the named volumes — this destroys the LDAP
> directory and the ZODB, so back up first (see **Backups** below).

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

### Runtime LDAP logging

The LDAP entrypoint (`start_ldap.sh`) has two independent **runtime** flags
(set them in `docker/.env` or the service `environment:`):

| Flag | Effect |
|---|---|
| `DEBUG_LDAP=true` | Verbose, **secret-safe** logs, and raises slapd to `-d 256` (stats). The admin password is shown as `<hidden>`. |
| `DEBUG_PASSWORD_LDAP=true` | Enables shell `xtrace` and prints `LDAP_PASSWORD` **in cleartext** in the container logs. |

> **Security:** never commit `DEBUG_PASSWORD_LDAP=true`. Use it only for a
> one-off local diagnosis, then rotate the password and delete the logs that
> captured it. At the default (`false`), no secret ever reaches the logs, and
> slapd runs at `-d 0` (foreground, no verbose stats).

---

## Manual operation (without Compose)

Useful for troubleshooting or rebuilding a single service. Source the env file
first:

> **Networks:** the Compose stack now creates `alirpunkto-frontend` and
> `alirpunkto-backend` (not the old single `alirpunkto-backend`). The examples below
> use `alirpunkto-backend` for LDAP/Postfix/Pyramid and `alirpunkto-frontend`
> for Apache; a fully manual stack needs Pyramid on **both** networks (add a
> second `--network alirpunkto-frontend`). Create a missing network with
> `docker network create <name>`. Bind internal services to `127.0.0.1` as the
> Compose stack does.

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
  --network alirpunkto-backend \
  -p 127.0.0.1:8389:389 \
  -p 127.0.0.1:8636:636 \
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
  --network alirpunkto-backend \
  -p 127.0.0.1:6543:6543 \
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
  --network alirpunkto-frontend \
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

With `ENABLE_CERTBOT=true`, `start_apache2.sh` also renews the certificate
**periodically** (**R3**): a background `certbot renew` runs every 12 h and
reloads Apache gracefully only when the certificate actually changes, so a
long-running container never ends up serving an expired certificate.

### Postfix

> **Do not publish port 25.** Postfix is send-only and is reached by Pyramid
> over `alirpunkto-backend`; mapping `-p 9025:25` on `0.0.0.0` re-opens the relay to
> the Internet. See "Postfix — security notes" below.

```bash
docker build -f docker/DockerfilePostfix -t alirpunkto-postfix .

docker volume create alirpunkto_postfix_spool
docker volume create alirpunkto_postfix_dkim

docker run -d --name alirpunkto-postfix \
  --network alirpunkto-backend \
  -e DOMAIN="$DOMAIN" \
  -e POSTFIX_MYHOSTNAME="$POSTFIX_MYHOSTNAME" \
  -v alirpunkto_postfix_spool:/var/spool/postfix \
  -v alirpunkto_postfix_dkim:/etc/dkimkeys \
  alirpunkto-postfix
```

Optional variables: `POSTFIX_RELAYHOST`, `POSTFIX_INET_PROTOCOLS`,
`POSTFIX_MESSAGE_SIZE_LIMIT`, `POSTFIX_MYNETWORKS`, `FAILOVER_IP`.

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
  -W \
  -b "$LDAP_BASE_DN" \
  "(objectClass=inetOrgPerson)"
```

> `-W` prompts for the password instead of passing it on the command line
> (`-w …`), so it does not leak into the shell history or the process list.

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

---

## Backups

`docker/backup.sh` (**R4**) dumps the two stateful stores and rotates old
archives:

- **LDAP** → `slapcat` of the config (`-n 0`) and data (`-n 1`) databases (LDIF);
- **ZODB** → a hot copy of `Data.fs` (append-only, so copying a live file is safe).

Run it from the host (it drives the containers via `docker`), e.g. daily from
cron:

```bash
0 3 * * *  /path/to/repo/docker/backup.sh >> /var/log/alirpunkto-backup.log 2>&1
```

Overrides: `BACKUP_DIR` (default `/var/backups/alirpunkto`), `KEEP_DAYS`
(default 14), `LDAP_CONTAINER`, `PYRAMID_CONTAINER`, `ZODB_PATH`. Each run writes
a timestamped `*.tar.gz` and prunes archives older than `KEEP_DAYS`. **Copy the
archives off-host and test a restore periodically** — restore notes (slapadd /
replacing `Data.fs`, plus `repozo` for point-in-time ZODB snapshots) are at the
bottom of `backup.sh`.

---

# Postfix — security notes

## Migrating a legacy LDAP directory

`docker/migrate_ldap_legacy.py` adapts an export of a pre-2026 AlirPunkto
directory to the current schema: `employeeType` values are normalised to the
`MemberTypes` names (including the historic `coperator` typo and value-form
variants), the `coperatorsGroup`/`communityGroup` groups are renamed and their
references rewritten, `gn` becomes `givenName`, `isActive` is canonicalised,
operational attributes are stripped and referential consistency is checked.
The 2026-07 field runs added three data repairs: dangling
`providerMembersGroup` references are renamed to `providersGroup`, group
members wrongly parented under `cn=admin` are re-parented to their actual
entry (the all-zero placeholder is the one intentional `cn=admin` member and
is left alone), and literal `None` descriptions are dropped.

The pipeline can be fed from three sources. `docker/migrate_ldap_legacy.py`
itself reads a file (`--input`) or runs `slapcat` (in a container with
`--slapcat-container`, or locally with `--slapcat-local`) — both need
filesystem access to the directory. When the legacy server is a **bare-metal
host you can only reach over the network**, use
`tools/migrate_ldap_legacy_remote.py` instead: it binds with the
administrator credentials of the project `.env` (`LDAP_SERVER`, `LDAP_LOGIN`,
`LDAP_BASE_DN`, `LDAP_PASSWORD`…), extracts the whole subtree with a paged
search, then hands the entries to this very same pipeline, so both paths
produce the same adapted LDIF.

Since finding 1.3 was fixed, the script also **hashes every cleartext
`userPassword` to `{SSHA}`** (values already hashed are kept verbatim), so the
adapted LDIF can be loaded without ever storing a cleartext password. Logins
are unaffected: authentication is an LDAP *bind*, and slapd verifies `{SSHA}`
natively. Pass `--keep-cleartext-passwords` only if you need a verbatim copy
of the export (for inspection — do not load it in production).

```bash
# 1. export and adapt the legacy directory (pick one input mode)
python3 docker/migrate_ldap_legacy.py --slapcat-container old-ldap \
    --output adapted.ldif --report report.txt
python3 docker/migrate_ldap_legacy.py --input old.ldif \
    --output adapted.ldif --report report.txt

# 2. read report.txt, then load into the current stack
docker cp adapted.ldif alirpunkto-ldap:/tmp/adapted.ldif
docker exec alirpunkto-ldap ldapadd -Y EXTERNAL -H ldapi:/// \
    -f /tmp/adapted.ldif
```

`--strict` makes the script exit non-zero on any unknown `employeeType` or
unresolved reference instead of warning.

## One-shot provisioning: extract, seed file, schema, users, ZODB

`tools/ldap_provision.py` chains the whole journey for an administrator who
wants to (re)provision an installation from a live directory. It always
extracts over the network with the `.env` admin credentials and adapts with
the pipeline above (`{SSHA}` hashing included), then acts on demand:

```bash
# Bare-metal host, end to end: seed file + schema + users
python tools/ldap_provision.py --install-type host --sudo \
    --update-schema --load --report provision.txt

# Docker: refresh the seed file for the next container initialisation
python tools/ldap_provision.py --install-into-docker

# Docker: also (re)create the users in the RUNNING container
python tools/ldap_provision.py --install-type docker --load

# Legacy directory kept in place: just hash its cleartext passwords
python tools/ldap_provision.py --update-passwords-in-place
```

**Interchangeable seed file.** The output (default
`./initials_users.generated.ldif`) is interchangeable with the file
`docker/init.sh` generates: copy it to
`docker/initials_users.generated.ldif` (or pass `--install-into-docker`) and
the compose stack seeds the container with your real users at the next
initialisation — `start_ldap.sh` loads it with `ldapadd -c`, so the groups it
shares with the template are simply reported as already existing.

**The admin chooses the installation type.** `--update-schema` and `--load`
require `--install-type {docker,host}`: commands run through `ldapi:///` +
SASL EXTERNAL inside the container (`--container`, default `alirpunkto-ldap`)
or on the host (usually with `--sudo`, since `cn=config` needs root).

**Forcing the schema.** `--update-schema` discovers the
`cn={N}alirpunktoperson,cn=schema,cn=config` entry and *replaces* its
attribute/objectClass definitions with the repo's current
`alirpunkto/alirpunkto_schema.ldif` (idempotent — safe to run twice; the
entry is added wholesale if absent), then verifies through a fresh bind that
the modern attributes (`cooperativeBehaviourMarkUpdate`, `IBAN`,
`dateErasureAllData`) are known. This is the definitive fix for the
`invalid attribute type cooperativeBehaviourMarkUpdate` login error on
legacy servers.

**Hashing passwords in place.** `--update-passwords-in-place` closes finding
1.3 on a directory you keep as-is: every account whose stored `userPassword`
is still cleartext gets a `MODIFY_REPLACE` with the `{SSHA}` value computed
by the pipeline, over the same authenticated connection. Hashed values are
skipped, so this too is idempotent.

**Repopulating the ZODB.** Once the directory is provisioned, the
application rebuilds its object store by itself: stop AlirPunkto, move the
old store away (`mv var var.bak`, then `mkdir -p var/filestorage var/blobs
var/log` on a bare-metal host) and start again. At each user's first login,
`update_member_from_ldap` recreates the member from the LDAP entry — type
and profile included, `password`/`password_confirm` kept to `None` (finding
1.3). This lazy repopulation is locked by
`tests/test_zodb_repopulation_from_ldap.py`.

## Purging cleartext passwords from the ZODB

Candidatures created before the 1.3 fix persisted the applicant's password
(and its `password_confirm` copy) in cleartext inside `Data.fs`.
`tools/purge_zodb_cleartext_passwords.py` cleans this up: entries whose LDAP
account already exists — or never will (APPROVED/REFUSED, plain members) — get
their password cleared, while still-pending candidatures are hashed in place
so their approval can still create the LDAP account.

Stop the Pyramid container first (FileStorage is single-writer) and take a
backup (`docker/backup.sh`), then:

```bash
python tools/purge_zodb_cleartext_passwords.py \
    --data-fs var/filestorage/Data.fs --dry-run   # review the plan
python tools/purge_zodb_cleartext_passwords.py \
    --data-fs var/filestorage/Data.fs             # apply
```

## Do not publish port 25

Postfix is **send-only** for AlirPunkto notifications and is reached by Pyramid
over the internal `alirpunkto-backend` (`alirpunkto-postfix:25`). It does **not** need
a published port. The Compose stack no longer maps `9025:25`.

If you use the manual `docker run` example, **remove** `-p 9025:25` (publishing 25
on `0.0.0.0` exposes the relay to the Internet). Only publish it if this host must
be an inbound MX — and then bind it explicitly to the public IP, add a host
firewall, and enable SASL authentication.

```bash
# send-only (recommended): no port mapping, no POSTFIX_MYNETWORKS needed
docker run -d --name alirpunkto-postfix --network alirpunkto-backend \
  -e DOMAIN="<your-domain>" \
  -e POSTFIX_MYHOSTNAME="<your-hostname>" \
  -v alirpunkto_postfix_spool:/var/spool/postfix \
  -v alirpunkto_postfix_dkim:/etc/dkimkeys \
  alirpunkto-postfix
```

### `POSTFIX_MYNETWORKS` and the relay perimeter

Left unset (the default), `start_postfix.sh` auto-detects this container's own
bridge subnet and trusts it. **This is safe precisely because port 25 is not
published:** with no external ingress, only the stack's own containers on
`alirpunkto-backend` can reach Postfix, so trusting that private subnet cannot become
an Internet-facing open relay.

The danger only appears **if you publish port 25**: Docker NAT then makes external
connections look like they come from the bridge gateway (inside the auto-detected
subnet), so trusting a whole `/16` (≈ 65 000 addresses) opens the relay to the
world. **If — and only if — you publish port 25**, do one of:

- set `POSTFIX_MYNETWORKS` to a tight, explicit range (e.g. just the Pyramid
  container's address), **or**
- enable SASL authentication and drop `permit_mynetworks`.

## Verify the relay is closed

From an **external** host (open-relay test — expect a rejection):

```bash
swaks --server <public-ip>:25 --from spammer@evil.example --to target@gmail.com
# Expected: 554 5.7.1 <target@gmail.com>: Relay access denied
```

From the host (effective settings):

```bash
docker exec alirpunkto-postfix postconf mynetworks smtpd_relay_restrictions inet_interfaces
docker exec alirpunkto-postfix ss -ltnp | grep ':25'   # must NOT be exposed publicly
```

## DNS records to publish

The container prints the DKIM public key on first start
(`docker exec alirpunkto-postfix cat /etc/dkimkeys/dkim.txt`). To send mail
without being flagged as spam and to limit spoofing, publish **all four** records
for `<your-domain>`:

| Type | Name | Value (example) | Purpose |
|---|---|---|---|
| TXT | `dkim._domainkey.<domain>` | `v=DKIM1; k=rsa; p=<public-key>` | DKIM signing key |
| TXT | `<domain>` | `v=spf1 ip4:<sending-ip> -all` | SPF: authorize the sending IP, reject the rest |
| TXT | `_dmarc.<domain>` | `v=DMARC1; p=quarantine; rua=mailto:postmaster@<domain>` | DMARC policy + reports |
| PTR | reverse of `<sending-ip>` | `<your-hostname>` | rDNS/PTR matching `myhostname` (FCrDNS) |

Notes:
- **SPF**: list every IP that sends for the domain; `-all` (hard fail) is the
  strong policy once the list is complete (use `~all` while validating).
- **DMARC**: start with `p=none` to observe via `rua=` reports, then move to
  `p=quarantine`/`p=reject`.
- **rDNS/PTR** must match `POSTFIX_MYHOSTNAME`, and forward-confirmed reverse DNS
  (PTR ↔ A) is often required by large providers (Gmail, Outlook…).
- **OpenDKIM** signs `*@${DOMAIN}`. With the relay closed this is safe; if you
  ever expose the MX, scope `InternalHosts`/`ExternalIgnoreList` in
  `opendkim.conf` so only genuinely internal traffic is signed (otherwise a
  spammer could get the domain to sign their spam).