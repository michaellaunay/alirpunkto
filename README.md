# AlirPunkto

AlirPunkto ("Access Point" in Esperanto) is a Python/Pyramid web application for
cooperative membership and account management.

It provides a moderated registration workflow, LDAP-backed member storage, voting
and verification flows for candidatures, password reset and email-change flows,
optional SSO/Keycloak integration, and Docker-based deployment helpers.

## Main stack

AlirPunkto is built with:

- Python 3 and Pyramid;
- Chameleon / TAL-METAL templates;
- ZODB for application state;
- OpenLDAP for member and group data;
- Postfix for application e-mail delivery;
- Apache as HTTPS reverse proxy;
- Bootstrap 5 for the UI;
- optional Keycloak / SSO integration.

The application enables CSRF protection globally and uses secure session cookies.
For local functional tests and local Docker runs, make sure requests are made over
HTTPS-compatible URLs and that forms include their CSRF token.

## Repository layout

```text
alirpunkto/                  Pyramid application package
alirpunkto/models/           Persistent member, candidature and permission models
alirpunkto/views/            Pyramid views
alirpunkto/templates/        Chameleon templates
alirpunkto/schemas/          Deform/Colander form schemas
tests/                       Self-contained unit and functional regression tests
docker/                      Production and local Docker stacks
docker/README.md             Full Docker deployment documentation
docker/README_TEST_LOCAL.md  Local/offline Docker test stack documentation
tools/                       Developer helper scripts
docs/                        Project documentation and design notes
```

The documentation in `docs/` is written as Markdown notes. Some files use
Obsidian-style links such as `[[A Name]]`, which point to a Markdown file named
`A Name.md`.

## Quick start for development

From a clean checkout:

```bash
git clone git@github.com:michaellaunay/alirpunkto.git
cd alirpunkto
```

Create and activate a virtual environment. The existing project convention uses
a virtual environment directly at the repository root, which creates `bin/`,
`lib/`, and related directories there:

```bash
python3 -m venv .
source bin/activate
```

Upgrade packaging tools and install the project with its test dependencies:

```bash
bin/pip install --upgrade pip setuptools wheel
bin/pip install -e ".[testing]"
```

Create the runtime directories used by the application:

```bash
mkdir -p var/log var/datas var/filestorage var/sessions
```

Create your local environment file:

```bash
cp .env.example .env
python3 alirpunkto/generate_secret.py
```

Copy the generated `SECRET_KEY` into `.env`, then review the other values such as
LDAP, mail, site name, domain name and optional Keycloak settings.

Do not commit local `.env` files, generated secrets, certificates, LDIF files, or
local `test.ini` files.

## Running the tests

The default pytest suite is self-contained. It mocks LDAP-facing startup side
effects and does not start Docker unless explicitly requested.

Run:

```bash
bin/pytest
```

To point the Pyramid functional tests to a specific INI file:

```bash
bin/pytest --ini testing.ini
```

If `testing.ini` is absent, the affected functional tests are skipped.

Some regression tests validate the local Docker stack files themselves, but they
do not start the Docker stack. To run tests against an externally started LDAP
service, use the dedicated option only after starting that service:

```bash
bin/pytest --use-docker-ldap
```

## Running the application locally without Docker

After installing the project and creating `.env`:

```bash
bin/pserve development.ini
```

This mode expects the services referenced in `.env` to be reachable, especially
LDAP and mail.

## Local Docker test stack

For day-to-day local integration testing, use the dedicated test stack:

```bash
chmod +x docker/init_test.sh docker/start_test_*.sh docker/stop_clean_test.sh
./docker/init_test.sh
```

Add the local hostnames:

```bash
grep alirpunkto.localhost /etc/hosts || \
sudo sh -c 'printf "\n127.0.0.1 alirpunkto.localhost alirpunkto.local mail.alirpunkto.localhost\n" >> /etc/hosts'
```

Start the stack:

```bash
docker compose --env-file docker/.env.test -f docker/test-docker-compose.yaml up -d --build
```

Open:

```text
https://alirpunkto.localhost:8443/
```

The certificate is self-signed; a browser warning is expected.

The local test stack is separate from the production stack. It uses dedicated
container names, volumes and network, generates local credentials, runs Postfix
as a sink that accepts mail without relaying it, and binds debug ports to
`127.0.0.1` only.

`docker/init_test.sh` generates local-only files including:

```text
docker/.env.test
docker/secrets/ldap_password_test
docker/initials_users.test.generated.ldif
docker/certs/local-test/fullchain.pem
docker/certs/local-test/privkey.pem
test.ini
```

These files are generated artifacts and should not be committed.

The generated `test.ini` must make Waitress listen on the Docker container
network:

```ini
[server:main]
use = egg:waitress#main
listen = 0.0.0.0:6543
url_scheme = https
```

Do not use `listen = localhost:6543` in the Docker test stack: from Apache,
`localhost` would mean the Apache container itself, not the Pyramid container.

For detailed troubleshooting, port mappings, generated test accounts and cleanup
commands, see:

```text
docker/README_TEST_LOCAL.md
```

## Production Docker stack

The production-oriented Docker stack is documented in:

```text
docker/README.md
```

Typical first-time setup:

```bash
chmod +x docker/init.sh
./docker/init.sh
```

Then start the stack from the repository root:

```bash
docker compose --env-file docker/.env -f docker/docker-compose.yaml up -d
```

The production stack starts OpenLDAP, Postfix, Pyramid and Apache with dedicated
healthchecks and named volumes.

Generated production files such as `docker/.env`,
`docker/secrets/ldap_password` and `docker/initials_users.generated.ldif` contain
deployment-specific material and must not be committed.

## OpenLDAP schema

AlirPunkto uses the custom schema:

```text
alirpunkto/alirpunkto_schema.ldif
```

The Docker OpenLDAP image loads this schema automatically.

For a manual OpenLDAP installation, install and load the schema on the LDAP
server, then verify the resulting schema and group layout before pointing
AlirPunkto at it. Always test schema changes in a development environment and
back up the LDAP configuration before modifying a production directory.

## Source export for review

Developer review dumps can be generated with:

```bash
tools/export_sources_for_review.sh
```

The script exports selected source files to a numbered text file under `/tmp/`.
It intentionally excludes generated, local, binary and sensitive artifacts such
as `.env*`, certificates, private keys, generated LDIF files, caches, locale
build artifacts, static assets and local `test.ini`.

## Common commands

```bash
# Run tests
bin/pytest

# Run the development server
bin/pserve development.ini

# Start the production Docker stack
docker compose --env-file docker/.env -f docker/docker-compose.yaml up -d

# View production Docker logs
docker compose --env-file docker/.env -f docker/docker-compose.yaml logs -f

# Start the local Docker test stack
docker compose --env-file docker/.env.test -f docker/test-docker-compose.yaml up -d --build

# View local Docker test logs
docker compose --env-file docker/.env.test -f docker/test-docker-compose.yaml logs -f

# Stop and remove local Docker test containers and volumes
./docker/stop_clean_test.sh
```

## Security notes

- Keep `.env`, generated LDAP passwords, certificates and generated LDIF files
  out of Git.
- Use HTTPS in deployed environments.
- Review `production.ini` and `docker/.env` before deployment.
- Configure mail delivery intentionally; the local test stack never relays mail.
- Configure Keycloak/SSO variables only when SSO is actually enabled.
- Do not reuse local test credentials in production.

## Documentation

Main documentation lives in:

```text
docs/fr/
docs/en/
```

Docker-specific documentation lives in:

```text
docker/README.md
docker/README_TEST_LOCAL.md
```
