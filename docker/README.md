# Docker Images

This directory contains the Dockerfiles and startup scripts for the main Alirpunkto services:

- `DockerfileOpenLDAP`
- `DockerfilePyramid`
- `DockerfileApache2`
- `DockerfilePostfix`

## Prerequisites

- Run the commands from the repository root unless noted otherwise.
- Create a dedicated Docker network so the containers can resolve each other by name:

```bash
docker network create alirpunkto-net
```

- If you want to customize runtime settings, copy your main `.env` file to `docker/.env` and adjust it for container usage.

## OpenLDAP

For security reasons, store the LDAP password in `docker/secrets/ldap_password`.

Example preparation:

```bash
mkdir -p docker/secrets
chmod 700 docker/secrets
cp .env docker/.env
set -a
source docker/.env
set +a
umask 077
printf '%s' "$LDAP_PASSWORD" > docker/secrets/ldap_password
sed "s|dc=alirpunkto,dc=org|${LDAP_BASE_DN}|g" \
  docker/initials_users.ldif > docker/initials_users.generated.ldif
```

Build the image:

```bash
docker buildx build -f docker/DockerfileOpenLDAP -t alirpunkto-ldap docker
```

Create persistent volumes:

```bash
docker volume create alirpunkto_ldap_etc
docker volume create alirpunkto_ldap_var
```

Run the container:

```bash
docker run --name alirpunkto-ldap \
  --network alirpunkto-net \
  -p 8389:389 \
  -p 8636:636 \
  -e LDAP_BASE_DN="$LDAP_BASE_DN" \
  -e LDAP_ORGANIZATION="$LDAP_ORGANIZATION" \
  -e LDAP_PASSWORD_FILE=/run/secrets/ldap_password \
  -v "$(pwd)/alirpunkto/alirpunkto_schema.ldif:/schema/alirpunkto_schema.ldif:ro" \
  -v alirpunkto_ldap_etc:/etc/ldap \
  -v alirpunkto_ldap_var:/var/lib/ldap \
  -v "$(pwd)/docker/secrets/ldap_password:/run/secrets/ldap_password:ro" \
  alirpunkto-ldap
```

If you need a clean LDAP reinitialization:

```bash
docker rm -f alirpunkto-ldap
docker volume rm alirpunkto_ldap_etc
docker volume rm alirpunkto_ldap_var
```

## Pyramid

`DockerfilePyramid` copies the whole project into the image, so its build context must be the repository root.

Build the image:

```bash
docker build -f docker/DockerfilePyramid -t alirpunkto-pyramid .
```

Create a persistent volume for application data:

```bash
docker volume create alirpunkto_pyramid_var
```

Run the container:

```bash
docker run --name alirpunkto-pyramid \
  --network alirpunkto-net \
  -p 6543:6543 \
  -e LDAP_SERVER=alirpunkto-ldap \
  -e LDAP_PORT=389 \
  -e MAIL_HOST=alirpunkto-postfix \
  -v alirpunkto_pyramid_var:/home/alirpunkto/app/var \
  -v "$(pwd)/.env:/home/alirpunkto/app/.env:ro" \
  alirpunkto-pyramid
```

Notes:

- The container starts `pserve production.ini` by default.
- If needed, you can override the configuration file:

```bash
docker run --rm alirpunkto-pyramid development.ini
```

## Apache2

This image provides a generic TLS reverse proxy for the Pyramid container. The repository also contains a client-specific reference file named `alirpunkto.cosmopolitical.coop.conf`; it is kept as documentation and is not enabled automatically by the generic image.

Build the image:

```bash
docker build -f docker/DockerfileApache2 -t alirpunkto-apache2 docker
```

Create persistent volumes for Let's Encrypt data:

```bash
docker volume create alirpunkto_apache_letsencrypt
docker volume create alirpunkto_apache_letsencrypt_lib
```

Run the container:

```bash
docker run --name alirpunkto-apache2 \
  --network alirpunkto-net \
  -p 8080:80 \
  -p 8443:443 \
  -e APACHE_SERVER_NAME=alirpunkto.com \
  -e APACHE_BACKEND_HOST=alirpunkto-pyramid \
  -e APACHE_BACKEND_PORT=6543 \
  -e ENABLE_CERTBOT=false \
  -v alirpunkto_apache_letsencrypt:/etc/letsencrypt \
  -v alirpunkto_apache_letsencrypt_lib:/var/lib/letsencrypt \
  alirpunkto-apache2
```

To let the container request certificates itself, set:

```bash
-e ENABLE_CERTBOT=true \
-e LETSENCRYPT_EMAIL=admin@example.org
```

## Postfix

This image is intended for SMTP submission/relay from the application side and generates DKIM keys on first start if none are mounted.

Build the image:

```bash
docker build -f docker/DockerfilePostfix -t alirpunkto-postfix docker
```

Create persistent volumes:

```bash
docker volume create alirpunkto_postfix_spool
docker volume create alirpunkto_postfix_dkim
```

Run the container:

```bash
docker run --name alirpunkto-postfix \
  --network alirpunkto-net \
  -p 9025:25 \
  -e DOMAIN=alirpunkto.com \
  -e POSTFIX_MYHOSTNAME=mail.alirpunkto.com \
  -v alirpunkto_postfix_spool:/var/spool/postfix \
  -v alirpunkto_postfix_dkim:/etc/dkimkeys \
  alirpunkto-postfix
```

Optional variables:

- `POSTFIX_RELAYHOST=[smtp.provider.example]:587`
- `POSTFIX_INET_PROTOCOLS=ipv4`
- `POSTFIX_MESSAGE_SIZE_LIMIT=26214400`
- `FAILOVER_IP=x.x.x.x`

On first start, the container prints the DKIM DNS record to the container logs:

```bash
docker logs alirpunkto-postfix
```

## Suggested Startup Order

Start the services in this order:

1. `alirpunkto-ldap`
2. `alirpunkto-postfix`
3. `alirpunkto-pyramid`
4. `alirpunkto-apache2`

## Logs

The current strategy is to rely on container stdout/stderr instead of persisting log files inside containers:

```bash
docker logs -f alirpunkto-ldap
docker logs -f alirpunkto-postfix
docker logs -f alirpunkto-pyramid
docker logs -f alirpunkto-apache2
```
