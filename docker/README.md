For security reason, you must place the admin password in the host file secrets/ldap_password, located in the installation base directory.
To manualy create ldap contener do :

```bash
docker build -f docker/DockerfileOpenLDAP  -t alirpunkto-ldap docker
docker run --name alirpunkto-ldap \
  -p 389:389 -p 636:636 \
  -e LDAP_BASE_DN="$LDAP_BASE_DN" \
  -e LDAP_ORGANIZATION="$LDAP_ORGANIZATION" \
  -e LDAP_PASSWORD_FILE=/run/secrets/ldap_password \
  -v alirpunkto_ldap_data:/var/lib/ldap \
  -v alirpunkto_ldap_conf:/etc/ldap \
  -v $(pwd)/secrets/ldap_password:/run/secrets/ldap_password:ro \
  alirpunkto-ldap
```
