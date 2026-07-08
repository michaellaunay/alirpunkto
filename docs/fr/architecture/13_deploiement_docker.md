# Déploiement Docker

> Statut : documentation courante — **synthèse**. Le document de référence,
> maintenu au fil des audits, est `docker/README.md` ; la pile de test
> locale est décrite dans `docker/README_TEST_LOCAL.md`. Le présent
> document ne duplique pas leurs procédures.

## Services

La pile `docker/docker-compose.yaml` comprend quatre services :

- **apache2** : frontal HTTPS (certificats Let's Encrypt, volumes dédiés) ;
- **pyramid** : l'application AlirPunkto (Waitress) ;
- **ldap** : OpenLDAP, schéma `alirpunktoPerson` chargé à l'initialisation ;
- **postfix** : relais sortant durci (DKIM, anti-relais, port 25 non
  publié).

Keycloak n'est **pas** dans la pile : c'est un service externe optionnel,
configuré par les variables `KEYCLOAK_*` du `.env`.

## Initialisation et amorçage

`docker/init.sh` prépare l'environnement : dérivation des variables,
génération de `docker/initials_users.generated.ldif` (comptes d'amorçage)
via `docker/generate_ldif.py`, mise en place du schéma. Les scripts
`start_*.sh` démarrent chaque service. Le fichier d'amorçage est
**interchangeable** avec celui produit par `tools/ldap_provision.py` depuis
un annuaire existant (migration d'une instance réelle).

## Données et sauvegardes

Les données vivent dans des volumes nommés (`alirpunkto_ldap_*`,
`alirpunkto_pyramid_var`, `alirpunkto_postfix_*`, certificats Apache).
`docker/backup.sh` sauvegarde configuration et données ; procédure et
restauration dans `docker/README.md`.

## Déploiement sans conteneurs

Le déploiement nu (hôte unique) est pris en charge par le même outillage :
`tools/ldap_provision.py --install-type host` (schéma, comptes), Postfix et
slapd de l'hôte, `pserve` pour l'application.
