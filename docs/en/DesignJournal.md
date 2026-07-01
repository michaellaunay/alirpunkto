# 2025-10-05

@TODO fix the following problem:
Comment regarding `alirpunkto/constants_and_globals.py:24` (and the surrounding block up to approximately line 160): almost all operational settings are loaded directly from environment variables or `.env` entries at module import time. For example: LDAP host/port, administrator credentials, Keycloak endpoints, and mail settings. No guard checks whether a value is missing or malformed before other modules use it; most values are injected into the Pyramid configuration (`alirpunkto/__init__.py:178`) or LDAP helpers (`alirpunkto/ldap_factory.py:18`) long after import.

As a result, a subtle typo or a missing environment variable usually triggers an exception only when a code path dereferences the setting (for example, when building an LDAP distinguished name or sending an email), which may happen well after startup, or even only in specific roles/tests. This latency makes deployment failures harder to diagnose.

Adding a validation routine — or at least documenting required variables — at startup would detect configuration gaps early and provide clearer error messages.

# 2026-02-11 to 2026-02-13

### 1. Class Hierarchy Correction (Data Model)

- **Problem:** The `alirpunktoPerson` class was initially defined as `STRUCTURAL` while attempting to inherit from `inetOrgPerson`. However, the LDAP standard (RFC 4512) forbids direct derivation between two structural classes.
- **Solution:** Change `alirpunktoPerson` to **`AUXILIARY`**.
- **Optimization:** Clean up redundant attributes. Attributes already present in `inetOrgPerson` (such as `mail`, `uid`, `cn`, `sn`) were removed from the `alirpunktoPerson` definition to avoid schema conflicts, while remaining usable on the final entry through multiple object-class membership.

### 2. Compliance with OLC Format (Online Configuration)

- **Header correction:** Strict alignment with the **OLC** format for injection into `cn=config`.
- **Case sensitivity:** Corrected the `cn` identifier in the schema to ensure consistency between the Distinguished Name (`dn: cn=alirpunktoPerson...`) and the `cn: alirpunktoPerson` attribute.
- **Application interoperability:** Kept the `DirectoryString` format for dates (`birthdate`, `dateEndValidityYearlyContribution`) despite LDAP's preference for `GeneralizedTime`, to preserve compatibility with the client Drupal application's read limitations.

### 3. Docker Deployment Reliability

- **Persistence vs initialization:** Replaced the volume mount for initial data with a **`COPY`** instruction in the Dockerfile (`COPY ./initials_users.ldif /initials_users.ldif`). This ensures that the image is ready to use and contains its base data immutably.

- **Robustness of the startup script (`start_ldap.sh`):**
  - Added execution tracing (`set -x`) to make debugging easier through `docker logs`.
  - Implemented post-load checks through `ldapsearch` to confirm that critical attributes (for example `isActive`) are effectively present before completing startup.
  - Automated the loading of the `inetorgperson.ldif` schema if absent, because it is a mandatory dependency for `alirpunkto` users.

### 4. Final State of Initial Data

- **Group structure:** Creation of a complete group tree (`communityGroup`, `coperatorsGroup`, `boardMembersGroup`, etc.) using the `groupOfUniqueNames` class for rights management.
- **Test users:** Injection of the first members with all custom attributes: IBAN, number of cooperative shares (`numberSharesOwned`), and spoken languages.

# 2025-02-20

All comments and line breaks had to be removed from `alirpunkto/alirpunkto_schema.ldif` so that the LDAP schema could finally be loaded correctly by the Docker container. This is due to strict application of the `cn=config` LDIF format; otherwise OpenLDAP creates the entry but ignores the internal definitions.

Warning: mounting the schema as a volume allows the container to modify it directly if it is not passed with the `:ro` option during `docker run`. Be careful, because any modification made by `slapd` will be reflected in the host file.

# 2026-03-30

I do not have direct access to `Journal de conception.md`, but I have all the necessary context. Here is the entry to add:

---

```markdown
# 2025-03-30

## Docker Containerization of the AlirPunkto Stack

### Context

To make AlirPunkto easier to deploy on any machine without manually installing and configuring OpenLDAP, Postfix, Pyramid, and Apache, we built a complete Docker infrastructure. The goal is for a new administrator to deploy the project in two commands.

### What are Docker and Docker Compose?

**Docker** is a tool that packages an application and its entire environment (system, libraries, configuration) into an isolated box called a **container**. A container behaves the same way regardless of the host machine, eliminating the classic “it works on my machine” problem.

A container is created from an **image**, itself built from a text file called a `Dockerfile`, which describes the installation steps somewhat like a recipe.

**Docker Compose** is a complementary tool that describes in a single YAML file (`docker-compose.yml`) several containers that work together, their dependencies, persistent data volumes, and shared network. Instead of manually running 4 `docker run` commands in the correct order, we simply run:

```bash
docker compose -f docker/docker-compose.yml up -d
```

### Stack architecture

The AlirPunkto stack is made of four services that start in the following order, each waiting for the previous one to be operational before starting (the **healthcheck** mechanism):

```
alirpunkto-ldap ──┐
                  ├──► alirpunkto-pyramid ──► alirpunkto-apache2
alirpunkto-postfix┘
```

- **alirpunkto-ldap**: the OpenLDAP server that stores users and their roles. This is the most critical building block; all other services depend on it.
- **alirpunkto-postfix**: the mail server that lets the application send emails (application confirmations, password resets, etc.). It automatically generates a DKIM key on first startup.
- **alirpunkto-pyramid**: the web application itself, which starts only when LDAP and Postfix are ready.
- **alirpunkto-apache2**: the TLS reverse proxy that receives public HTTPS requests and forwards them to Pyramid. It can optionally request a Let's Encrypt certificate automatically.

### What is a healthcheck?

A healthcheck is a command Docker runs periodically inside a container to verify that it is truly operational, not merely started. For example, for LDAP:

```yaml
healthcheck:
  test: ["CMD", "ldapsearch", "-x", "-H", "ldap://localhost", "-s", "base", "-b", ""]
  interval: 10s     # checks every 10 seconds
  timeout: 5s       # fails if there is no response within 5 seconds
  retries: 5        # declares the service "unhealthy" after 5 consecutive failures
  start_period: 15s # ignores failures during the first 15 seconds
```

Without this mechanism, Pyramid would start before LDAP is ready to accept connections, and the application would crash at startup.

### Secret management

Passwords are never passed as cleartext environment variables in `docker-compose.yml`. Docker Compose provides a **secrets** mechanism: the password is stored in a file on the host (`docker/secrets/ldap_password`, mode 600) and mounted inside the container under `/run/secrets/ldap_password`, accessible only by the process that needs it.

### The `init.sh` script

Docker Compose does not provide an interactive interface for the first startup. We therefore created `docker/init.sh`, a shell script to run once before the first `docker compose up`. It asks the administrator a few questions (domain name, LDAP password, first two users and their roles) and automatically generates three files:

- `docker/.env`: all stack configuration variables
- `docker/secrets/ldap_password`: the LDAP password isolated in a protected file
- `docker/initials_users.generated.ldif`: the LDAP initialization file with the first two users, whose passwords are hashed through `slappasswd` (`{SSHA}` format) — never stored in cleartext

### Problems encountered and solutions

**Relative paths in docker-compose.yml**

A classic Docker Compose pitfall: bind-mount paths in `volumes` are relative to the **current directory at launch time**, not to the location of the `docker-compose.yml` file. Since we always launch from the repository root, all paths are therefore of the form `./alirpunkto/...` and `./docker/...`. An earlier version used `../alirpunkto/...` (relative to the `docker/` directory), which silently broke when launched from the root.

**Postfix healthcheck**

The `postfix status` command can return a success code even when the SMTP daemon is not yet listening on port 25. We replaced it with a direct port check:

```bash
ss -ltn | grep -q ':25'
```

This command actually verifies that a process is listening on port 25, which is the only criterion that matters for dependent services.

**Docker build context**

The Pyramid `Dockerfile` must copy the entire project into the image (Python sources, templates, translations, etc.). Its build context must therefore be the repository root, not the `docker/` directory. This is explicitly specified in Compose:

```yaml
build:
  context: .                        # repository root
  dockerfile: docker/DockerfilePyramid
```

**Debug mode in Dockerfiles**

In production, tools such as `vim` or `ldapvi` should not be present in images — they increase the attack surface and image size. But they are indispensable while debugging. We adopted the `BUILD_WITH_DEBUG` pattern, already used in `DockerfilePyramid`, and applied it to `DockerfileOpenLDAP`:

```dockerfile
ARG BUILD_WITH_DEBUG=0
RUN apt-get install -y slapd ldap-utils ... \
    && if [ "$BUILD_WITH_DEBUG" = "1" ]; then \
         apt-get install -y vim ldapvi; \
       fi
```

In production, build normally. In debug mode:

```bash
docker buildx build --build-arg BUILD_WITH_DEBUG=1 \
  -f docker/DockerfileOpenLDAP -t alirpunkto-ldap:debug .
```
```

# 2026-04-20

Encrypting LDAP passwords for the first users in the LDIF requires installing `slapd` on the host:

```bash
sudo apt-get install slapd
```

On the production server where we use docker-compose, `production.ini` must be adapted to the container network.

`listen = localhost:6543` is critical — inside a container, `localhost` does not route outside the container. Waitress must listen on `0.0.0.0:6543` to be reachable from Apache and from the healthcheck.

# 2026-04-23

To retrieve the DKIM key from the Postfix container:

```bash
zope@kuneagi02:~/alirpunkto$ docker logs alirpunkto-postfix | grep -A 10 "DNS record to publish"
[Init] DNS record to publish for DKIM:
dkim._domainkey IN TXT ( "v=DKIM1; h=sha256; k=rsa; "
postfix/postlog: warning: not owned by root: /var/spool/postfix/usr/lib
      "p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAxuC+zE5b7LW9ftbTeond5fiUSNJWBRCVSP4KlSozce3Hl7TOKgGkuwfT7rl0BGZZ7/i4Lg/DCKRAKXaN8L5cE10h2G68U47AYxD6nevwfJZ/QM2WAyvNyccntaO9IPxquzeXn3xNlUIkP9Zytn9UA62mc7fahwMHxoeQpFSFePO1BfUmPIo3TSsOlCIMB83pCO7zNLnAq4FEmr"
postfix/postlog: warning: not owned by root: /var/spool/postfix/usr/lib/zoneinfo
      "TniPz8iOEGWu6nmHiIIHMBGxloB4jMOzOIPBOJP5sTwe01UhXrF+17KNfxE90P9+ThcvsqaUKQunEB6xxnqXvuhvn3gaUFlX8iEcv3i9eVYJVBPY2VHw4Fh0gWhq11S3Tvz+6sFQIDAQAB" )  ; ----- DKIM key dkim for testalirpunkto.cosmopolitical.coop
postfix/postlog: warning: not owned by root: /var/spool/postfix/usr/lib/sasl2
[Init] Starting Postfix
postfix/postlog: starting the Postfix mail system
```

# 2026-06-13

After Claude Fable was released, we launched an audit that found nearly 80 anomalies where ChatGPT and Opus had found only 12. We decided to wait until the security bugs were fixed before adding this audit to the repository.

# 2026-06-14

Following the closure of Fable, we are using Opus 4.8 Max and GPT 5.5 Advanced to fix each item in the audit [20260613_alirpunkto_code_review_en](docs/en/20260613_alirpunkto_code_review_en.md).

# 2026-06-30

Only one security bug remains, which is currently not exploitable outside the Docker network: the audit is therefore published.

This last flaw will be addressed as soon as the functional level is sufficient, because §1.3 (passwords stored in cleartext — `userPassword` on the LDAP side and `data.password` in ZODB) is the largest security issue and requires redesigning the LDAP and ZODB integration; for now we only have 10 users.

# 2026-07-01

All blocking bugs from section §2 of the audit (2.1 to 2.12) are now fixed. The most important remaining issue was the lack of tests — it had indeed allowed a silent regression to slip through during the application of a fix (the `lang2`/`lang3` block of §2.6, which erased a member's second language). We therefore added a non-regression test suite covering every §2 fix: one file per fix, 63 tests, increasing the suite from 97 to 160 green tests. For each one, we verified that the test failed on the pre-fix code to ensure that it really catches the regression.

Remaining, apart from §1.3: a few non-blocking bugs (§2.8, 2.13, 2.14, 2.16, 2.17), transaction consistency (§3), and quality debt (§5).

# 2026-07-01 — Start of the architecture documentation refactoring

The historical AlirPunkto design documentation no longer accurately reflects the current project architecture.

The scenarios contained in the older documents mostly come from the initial project specifications and early design notes. They remain important for understanding the origin of the project, the initial assumptions and the design options considered in 2023-2024, but they must no longer be used as normative documentation.

The new documentation structure therefore explicitly separates:

- **historical specifications**, preserved for context and traceability;
- **current architecture documentation**, aligned with the current code;
- **current functional specifications**, describing the accepted business flows;
- **architecture decisions**, explaining technical choices and their rationale.

The selected name for the archive of old scenarios is:

```text
docs/fr/specifications_historiques/
docs/en/historical_specifications/
```

This name is preferred over `spec_initiales`, which was considered too short and ambiguous. It clearly states that these documents have historical value without being the functional or technical source of truth.

A bilingual documentation action plan is added:

```text
docs/fr/Plan de refonte documentaire.md
docs/en/Documentation Refactoring Plan.md
```

The architecture documentation will then be progressively rebuilt around the following topics:

- system overview;
- runtime architecture;
- domain model;
- ZODB persistence;
- OpenLDAP integration;
- authentication;
- authorization and permissions;
- email;
- third-party applications;
- periodic tasks;
- internationalization;
- security;
- tests;
- Docker deployment;
- architecture decisions.

The adopted rule is: code and tests are the technical source of truth; architecture documentation describes the current state; older scenarios are preserved for project history and no longer take precedence when discrepancies exist.
