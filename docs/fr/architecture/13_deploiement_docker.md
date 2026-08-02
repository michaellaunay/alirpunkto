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

## Blocages levés (audits externes, quatrième → huitième passages)

Les trois défauts qui arrêtaient la pile avant `pserve` (contrôle
`setup.py` disparu, option Waitress inconnue `use_forwarded_proto`,
écoute sur la boucle locale avec `trusted_proxy` inadapté au réseau
compose) sont **corrigés et verrouillés** : la pile a sa propre
configuration serveur, dérivée à l'exécution par
`docker/apply_server_overrides.py` quand `PYRAMID_LISTEN` /
`PYRAMID_TRUSTED_PROXY` sont posées (le compose les pose par défaut),
et un **smoke test Compose** de bout en bout prouve le trajet
Apache → Waitress jusqu'à la vraie adresse cliente vue par le limiteur
de connexions. L'image est **multiétape** : le venv installe le seul
verrou runtime en mode empreintes avec `--only-binary=:all:` (trois
sdists purs nommés en exception — tout futur sdist casse le build
explicitement), l'application y est installée **en wheel** (parité
prouvée fichier à fichier), et l'étape finale n'embarque ni
compilateur ni arborescence source — une **liste de copie explicite**
remplace `COPY .`, ce qui a réparé au passage une casse latente : le
helper d'overrides, exclu par `.dockerignore`, n'atteignait jamais
l'image. Les quatre bases sont épinglées par digest, avec un
**snapshot APT opt-in** (`ALIRPUNKTO_UBUNTU_SNAPSHOT`) pour la
reproductibilité stricte ; la pile de test monte son verrou
(`requirements-test.lock`) et `test.ini` en lecture seule. Chronique
complète :
`docs/fr/audits/20260801_audit_externe_chatgpt_alirpunkto_4e_passage.md`,
`…_6e_passage.md` et `20260802_…_8e_passage.md`.

## Déploiement sans conteneurs

Le déploiement nu (hôte unique) est pris en charge par le même outillage :
`tools/ldap_provision.py --install-type host` (schéma, comptes), Postfix et
slapd de l'hôte, `pserve` pour l'application.
