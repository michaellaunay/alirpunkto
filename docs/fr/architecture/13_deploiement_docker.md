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

## Blocages connus (audit externe, quatrième passage — 2026-08-01)

La pile décrite ci-dessus **ne démarre pas en l'état** : trois défauts
simples, invisibles des tests unitaires, l'arrêtent avant `pserve`.
Les scripts `start_pyramid.sh`/`start_test_pyramid.sh` exigent un
`setup.py` supprimé au profit de `pyproject.toml` ; `production.ini`
porte l'option `use_forwarded_proto`, inconnue de Waitress 3 (rejet
vérifié en `ValueError`) ; et `listen = localhost:6543` est
inatteignable depuis le conteneur Apache — lequel, vu de Waitress,
n'est pas non plus `127.0.0.1` (`trusted_proxy`), ce qui rabattrait le
limiteur de connexions sur une seule adresse. Le healthcheck interne,
qui interroge la boucle locale, peut rester vert pendant ce temps. Ces
valeurs restent les bonnes pour le déploiement nu ci-dessous ; la
correction (patch P0) donne à la pile sa propre configuration serveur
et ajoute le smoke test Compose qui aurait détecté les trois. L'image,
elle, installe le verrou complet — outils de test et de qualité
compris — après une mise à niveau hors verrou : la séparation des
verrous et l'image multiétape sont le P1. Détail, contre-expertise et
plan :
`docs/fr/audits/20260801_audit_externe_chatgpt_alirpunkto_4e_passage.md`.

## Déploiement sans conteneurs

Le déploiement nu (hôte unique) est pris en charge par le même outillage :
`tools/ldap_provision.py --install-type host` (schéma, comptes), Postfix et
slapd de l'hôte, `pserve` pour l'application.
