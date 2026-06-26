# AlirPunkto — Local Docker test stack without Internet access

This directory contains a local Docker stack for testing AlirPunkto on a development workstation.

The test stack is intentionally separated from the production stack:

- separate container names;
- separate named volumes;
- separate Docker network;
- local self-signed TLS certificate;
- local LDAP bootstrap data;
- Postfix in local sink mode;
- Apache reverse proxy available from the host browser;
- no external mail delivery.

The stack is designed to be started from the repository root.

---

## Prerequisites

Recommended:

```bash
docker --version
docker compose version
```

Use **Docker Compose v2** through:

```bash
docker compose
```

Avoid the old Python-based `docker-compose` v1 when possible. It may fail with recent Docker versions, especially with errors such as:

```text
KeyError: 'ContainerConfig'
```

If your system only has `docker-compose`, install the Docker Compose v2 plugin from the official Docker packages.

---

## Files added by the local test stack

The following files are committed or shared as part of the test setup:

```text
docker/
├── test-docker-compose.yaml
├── init_test.sh
├── start_test_apache2.sh
├── start_test_postfix.sh
├── start_test_pyramid.sh
├── stop_clean_test.sh
└── README_TEST_LOCAL.md
```

`init_test.sh` generates the local-only files below:

```text
docker/.env.test
docker/secrets/ldap_password_test
docker/initials_users.test.generated.ldif
docker/certs/local-test/fullchain.pem
docker/certs/local-test/privkey.pem
test.ini
```

Do not commit generated secrets, generated LDIF files, or local certificates unless this is intentional for a purely disposable demo environment.

---

## Local hostnames

Add these hostnames to `/etc/hosts`:

```bash
grep alirpunkto.localhost /etc/hosts || \
sudo sh -c 'printf "\n127.0.0.1 alirpunkto.localhost alirpunkto.local mail.alirpunkto.localhost\n" >> /etc/hosts'
```

The main test URL is:

```text
https://alirpunkto.localhost:8443/
```

The browser will warn about the certificate because it is self-signed. This is expected for the local test stack.

---

## First-time setup

From the repository root:

```bash
chmod +x docker/init_test.sh docker/start_test_*.sh docker/stop_clean_test.sh
./docker/init_test.sh
```

The initializer creates `test.ini` from `production.ini` or `development.ini` if `test.ini` does not already exist.

It must also normalize the Pyramid/Waitress bind address so that Apache can reach Pyramid inside Docker:

```ini
[server:main]
use = egg:waitress#main
listen = 0.0.0.0:6543
url_scheme = https
```

This is required. Do **not** use:

```ini
listen = localhost:6543
```

Inside Docker, `localhost` means “inside the Pyramid container only”. If Pyramid listens only on `localhost`, Apache will fail with:

```text
Service Unavailable
Apache/2.4.x Server at alirpunkto.localhost Port 8443
```

---

## Start the stack

Recommended command with Docker Compose v2:

```bash
docker compose --env-file docker/.env.test -f docker/test-docker-compose.yaml up -d --build
```

If your Compose version does not support `--env-file`, load the environment first:

```bash
set -a
source docker/.env.test
set +a

docker compose -f docker/test-docker-compose.yaml up -d --build
```

Check the result:

```bash
docker ps
```

Expected containers:

```text
alirpunkto-test-ldap
alirpunkto-test-postfix
alirpunkto-test-pyramid
alirpunkto-test-apache2
```

---

## Expected host port mappings

Apache must publish its ports on the host.

Expected output:

```bash
docker port alirpunkto-test-apache2
```

```text
80/tcp -> 127.0.0.1:8080
443/tcp -> 127.0.0.1:8443
```

If you see only this in `docker ps`:

```text
80/tcp, 443/tcp
```

then the container exists, but the ports are not published on the host. Recreate the stack:

```bash
docker compose --env-file docker/.env.test -f docker/test-docker-compose.yaml down
docker network rm alirpunkto-test-net 2>/dev/null || true
docker compose --env-file docker/.env.test -f docker/test-docker-compose.yaml up -d --build --force-recreate
```

If `--env-file` is not supported:

```bash
set -a
source docker/.env.test
set +a

docker compose -f docker/test-docker-compose.yaml down
docker network rm alirpunkto-test-net 2>/dev/null || true
docker compose -f docker/test-docker-compose.yaml up -d --build --force-recreate
```

---

## Open the application

Open in the browser:

```text
https://alirpunkto.localhost:8443/
```

Alternative HTTP endpoint:

```text
http://alirpunkto.localhost:8080/
```

Quick command-line test:

```bash
curl -kI https://127.0.0.1:8443/
```

`-k` is needed because the TLS certificate is self-signed.

---

## Test accounts

The default generated accounts are:

```text
admin.test / AdminTest123!
alice.test / AliceTest123!
bob.test   / BobTest123!
```

These credentials are for an isolated local test environment only. Never reuse them in production.

---

## Ports used on the Ubuntu development machine

Recommended local-only bindings:

```text
Apache HTTP:          127.0.0.1:8080  -> container 80
Apache HTTPS:         127.0.0.1:8443  -> container 443
Direct Pyramid debug: 127.0.0.1:16543 -> container 6543
LDAP debug:           127.0.0.1:18389 -> container 389
LDAPS debug:          127.0.0.1:18636 -> container 636
SMTP debug:           127.0.0.1:19025 -> container 25
```

Binding to `127.0.0.1` keeps the stack reachable only from the development workstation.

---

## Offline / no-Internet behaviour

The stack is intended for local testing without Internet access at runtime:

- Apache does not call Certbot;
- HTTPS uses the local self-signed certificate generated by `init_test.sh`;
- Postfix runs in sink mode and does not relay messages;
- LDAP and Pyramid communicate only through the Docker network;
- published ports are bound to `127.0.0.1`.

The Docker network may be declared as internal:

```yaml
networks:
  alirpunkto-test-net:
    name: alirpunkto-test-net
    driver: bridge
    internal: true
```

This prevents containers from reaching the Internet at runtime.

However, the existing Ubuntu-based Dockerfiles may run `apt-get` during image build. Therefore, build the images once while packages are available, or ensure the images are already present in the Docker cache. After that, restart offline with:

```bash
docker compose --env-file docker/.env.test -f docker/test-docker-compose.yaml up -d --no-build
```

---

## Logs and status

Show container status:

```bash
docker compose --env-file docker/.env.test -f docker/test-docker-compose.yaml ps
```

Follow logs:

```bash
docker compose --env-file docker/.env.test -f docker/test-docker-compose.yaml logs -f
```

Useful targeted logs:

```bash
docker logs --tail=120 alirpunkto-test-apache2
docker logs --tail=120 alirpunkto-test-pyramid
docker logs --tail=120 alirpunkto-test-ldap
docker logs --tail=120 alirpunkto-test-postfix
```

---

## Health checks

The Pyramid healthcheck should not only test `localhost:6543` from inside the Pyramid container.

A valid Docker-facing healthcheck should test the container IP, for example:

```yaml
healthcheck:
  test: ["CMD-SHELL", "python3 -c \"import socket, urllib.request; ip = socket.gethostbyname(socket.gethostname()); urllib.request.urlopen('http://%s:6543/' % ip, timeout=5)\""]
  interval: 15s
  timeout: 5s
  retries: 8
  start_period: 20s
```

This catches the common error where Pyramid listens on `localhost` only.

---

## Troubleshooting

### Browser says “connection failed”

Check that Apache ports are published on the host:

```bash
docker port alirpunkto-test-apache2
```

Expected:

```text
80/tcp -> 127.0.0.1:8080
443/tcp -> 127.0.0.1:8443
```

If no ports are listed, recreate the stack.

---

### Apache shows “Service Unavailable”

This means Apache is reachable from the browser, but Apache cannot reach Pyramid.

Check `test.ini` on the host:

```bash
grep -nA10 -E "^\[server:main\]" test.ini
```

Expected:

```ini
listen = 0.0.0.0:6543
```

Wrong:

```ini
listen = localhost:6543
```

Fix by rerunning:

```bash
./docker/init_test.sh
docker compose --env-file docker/.env.test -f docker/test-docker-compose.yaml up -d --build --force-recreate
```

---

### Check Apache → Pyramid without entering containers

Run this from the host:

```bash
docker exec alirpunkto-test-apache2 bash -lc '
python3 - <<PY
import urllib.request
urllib.request.urlopen("http://alirpunkto-test-pyramid:6543/", timeout=5)
print("Apache can reach Pyramid")
PY
'
```

If it fails with `Connection refused`, check the `listen` line in `test.ini`.

---

### Check Pyramid bind address without `ss` or `curl`

Run this from the host:

```bash
docker exec alirpunkto-test-pyramid bash -lc '
python3 - <<PY
import socket
for host in ["127.0.0.1", socket.gethostbyname(socket.gethostname())]:
    s = socket.socket()
    s.settimeout(2)
    try:
        s.connect((host, 6543))
        print(host, "OK")
    except Exception as e:
        print(host, "FAILED:", e)
    finally:
        s.close()
PY
'
```

Both addresses must be reachable. If only `127.0.0.1` works, Pyramid is still bound to localhost.

---

## Clean up

Remove local test containers and named volumes:

```bash
./docker/stop_clean_test.sh
```

If `stop_clean_test.sh` uses `docker compose --env-file` and your Compose version does not support it, run manually:

```bash
set -a
source docker/.env.test
set +a

docker compose -f docker/test-docker-compose.yaml down -v --remove-orphans
```

Generated files are kept:

```text
docker/.env.test
docker/initials_users.test.generated.ldif
docker/certs/local-test/
test.ini
```

Remove them manually only if you want a completely fresh local setup.

---

## Recommended validation sequence before sharing the stack

From a clean checkout:

```bash
./docker/init_test.sh

grep -nA10 -E "^\[server:main\]" test.ini

docker compose --env-file docker/.env.test -f docker/test-docker-compose.yaml down -v --remove-orphans || true
docker network rm alirpunkto-test-net 2>/dev/null || true
docker compose --env-file docker/.env.test -f docker/test-docker-compose.yaml up -d --build

docker ps
docker port alirpunkto-test-apache2
curl -kI https://127.0.0.1:8443/
```

Expected result:

```text
HTTP/1.1 200 OK
```

or another valid HTTP response from the application, but not:

```text
Connection refused
Service Unavailable
```
