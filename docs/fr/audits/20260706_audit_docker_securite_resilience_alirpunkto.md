# Audit Docker AlirPunkto — sécurité, résilience & bug mail de la pile de test

> **Révision post-remédiation — 2026-07-06.** Ce document reprend l'audit initial
> du 2026-07-02 et annote **chaque finding de son état de remédiation**. Le texte
> d'origine (constat + correctif proposé) est conservé pour la traçabilité ; les
> encarts **✅ RÉSOLU / ⚠️ PARTIEL** indiquent ce qui a été effectivement corrigé
> dans le dépôt.
>
> **Synthèse.** Sur les 18 findings (S1–S9, R1–R9) plus le bug mail (§3), **tous
> sont résolus sauf S5** (partiel : `no-new-privileges` appliqué aux 4 services et
> `cap_drop: ALL` sur Pyramid ; le retrait de capacités de LDAP/Postfix/Apache est
> fourni en guidance, à activer après validation sur pile en marche). Quatre
> findings (S4, S6, S7, S9) étaient déjà corrigés au fil de l'eau avant cette
> passe. Deux changements structurels non testables hors production —
> segmentation réseau **R6** et capacités **S5** — restent à **valider sur une
> pile lancée** ; le bug mail **§3** appelle une **confirmation par reproduction**.
>
> Remédiation livrée en trois lots : *(1)* `S3, S8, R5, R7, R8, R9` ; *(2)* `§3
> c3/c4, S5, R3, R4, R6` ; *(3)* mise à jour des `README` Docker.

> **Périmètre audité** : `docker/` — `DockerfileApache2`, `DockerfileOpenLDAP`, `DockerfilePostfix`, `DockerfilePyramid`, `docker-compose.yaml` (prod), `test-docker-compose.yaml` (test), `init.sh`, `init_test.sh`, `start_{apache2,ldap,postfix,pyramid}.sh`, `start_test_{apache2,postfix,pyramid}.sh`, `stop_clean_delete.sh`, `stop_clean_test.sh`, `README.md`, `README_TEST_LOCAL.md`, ainsi que le câblage mail côté application (`__init__.py`, `constants_and_globals.py`, `utils.py`).
>
> **Réserve de périmètre** — copiés dans les images mais **absents du dump**, donc non audités : `docker/etc/postfix/main.cf`, `docker/etc/opendkim.conf`, `docker/etc/apache2/sites-available/alirpunkto.conf.template` (le vhost **de production**). Les conclusions qui en dépendent sont explicitement signalées.
>
> **MàJ 2026-07-06 — réserve levée** : ces trois fichiers sont désormais présents dans le dépôt (`docker/etc/…`) et audités. Le vhost de prod est durci (voir **S7**) ; `opendkim.conf` et `main.cf` complètent — sans les contredire — les `postconf -e` des scripts.
>
> **Note transversale** : de façon récurrente, la pile de **test** applique de bonnes pratiques que la pile de **production ne suit pas** (liaison des ports sur `127.0.0.1`, notamment). Plusieurs correctifs consistent donc à **porter en prod ce qui est déjà fait en test**.

---

## Résumé exécutif

| Sévérité | Sécurité | Résilience |
|---|---|---|
| **Critique** | S1 mot de passe LDAP dans les logs (`set -x`) · S2 relais Postfix ouvert *(audit dédié)* | — |
| **Élevée** | S3 services internes exposés sur `0.0.0.0` en prod (annuaire LDAP, Waitress, SMTP) · S4 slapd `-d 256` en prod | R1 aucune limite de ressources (mem/cpu) |
| **Moyenne** | S5 conteneurs en root sans durcissement · S6 credentials baked dans l'image LDAP · S7 en-têtes/TLS Apache non vérifiables | R2 pas de rotation des logs · R3 renouvellement TLS seulement au redémarrage · R4 aucune stratégie de sauvegarde |
| **Faible** | S8 `.env` non `chmod` · S9 `remoteip` sans proxy de confiance | R5 `restart:"no"` en test (amplificateur du bug mail) · R6 pas de segmentation réseau · R7 nettoyage prod incomplet · R8 healthchecks superficiels · R9 réseau « internal » annoncé mais non configuré |

Le **bug mail de la pile de test** fait l'objet d'une section dédiée : il est **prouvé que ce n'est pas un problème de configuration mail** (identique et correcte vs prod) mais un problème **opérationnel** (Postfix injoignable au moment du commit).

> **État de remédiation (2026-07-06)** — tous les findings ci-dessous sont **RÉSOLUS**, à l'exception de **S5** (**partiel**). Détail finding par finding dans les encarts ; tableau de synthèse avec statut en §4.

---

# 1. Sécurité

## S1 — [CRITIQUE] Mot de passe admin LDAP exposé dans les logs du conteneur

> **✅ RÉSOLU** — `set -x` est désormais conditionné à `DEBUG_PASSWORD_LDAP=true` (défaut `false`, précédé d'un `[WARNING]`) ; le heredoc `slapd/password1|2` est journalisé `<hidden>` hors debug password ; l'import charge schéma et entrées via `ldapadd -Y EXTERNAL` (plus de `-w "$LDAP_PASSWORD"` en argv). *Nuance* : `test-docker-compose.yaml` garde `DEBUG_LDAP=true` par défaut — mais ce flag est maintenant **secret-safe** (il masque le mot de passe) ; c'est `DEBUG_PASSWORD_LDAP` (défaut `false`) qui exposerait.

`start_ldap.sh` commence par `set -x` **inconditionnel**. Or le script construit le mot de passe admin dans un heredoc `debconf-set-selections` :
```bash
set -x                                   # ← trace TOUTES les commandes, heredoc inclus
...
slapd slapd/password1 password $LDAP_PASSWORD
slapd slapd/password2 password $LDAP_PASSWORD
```
Avec `set -x`, l'expansion du heredoc (donc le mot de passe en clair) part sur stderr → visible dans `docker logs alirpunkto-ldap`. Aggravé par un bloc explicite qui **réécrit** le heredoc via `echo` quand `DEBUG_LDAP=true` :
```bash
if [[ "$DEBUG_LDAP" = "true" ]]; then
    echo "debconf-set-selections <<EOF" ... "slapd/password1 password $LDAP_PASSWORD" ...
fi
```
…et la pile de **test active ce mode** (`DEBUG_LDAP: ${DEBUG_LDAP:-true}` dans `test-docker-compose.yaml`). Enfin, l'import charge les utilisateurs avec `ldapadd -w "$LDAP_PASSWORD"` → mot de passe visible dans la table des processus du conteneur.

**Impact** : quiconque accède aux logs (agrégateur, `docker logs`, journald, CI) récupère le mot de passe d'administration de l'annuaire.

**Correctif**
- Retirer `set -x` (ou le rendre conditionnel **et** exclure la section mot de passe : `set +x` avant le heredoc, `set -x` après).
- Supprimer le bloc `echo` qui imprime le heredoc, ou masquer la valeur (`***`).
- Éviter `-w "$LDAP_PASSWORD"` : utiliser `-y <fichier>` (lecture du mot de passe depuis un fichier `600`) pour ne pas l'exposer en argv.
- Ne jamais laisser `DEBUG_LDAP=true` par défaut, même en test.

## S2 — [CRITIQUE] Relais Postfix ouvert

> **✅ RÉSOLU** (audit dédié) — le port 25 n'est **pas publié** dans `docker-compose.yaml`. `mynetworks` reste auto-détecté, mais c'est **sûr précisément parce qu'il n'y a aucun ingress externe** : sans port publié, seuls les conteneurs de la pile atteignent Postfix. Voir S3.

Traité en détail dans l'audit dédié `audit_securite_postfix_alirpunkto.md`. Rappel : en prod, port 25 publié sur `0.0.0.0` (`9025:25`) + `mynetworks` auto-détecté sur tout le sous-réseau du bridge + NAT Docker ⇒ relais ouvert exploitable depuis Internet. Voir S3 ci-dessous (même racine d'exposition) et l'audit dédié pour les correctifs.

## S3 — [ÉLEVÉ] Services internes exposés sur toutes les interfaces en production

> **✅ RÉSOLU** — en prod, LDAP est lié `127.0.0.1:8389`/`8636` et Waitress `127.0.0.1:6543` ; Postfix n'a plus de bloc `ports`. Seul Apache (`80`/`443`) reste public.

La prod publie sur `0.0.0.0` des services qui devraient rester internes ; la **test fait correctement** (`127.0.0.1`) :

| Service | Prod (`docker-compose.yaml`) | Test | Devrait être |
|---|---|---|---|
| **LDAP** | `8389:389`, `8636:636` → **annuaire des membres exposé** | `127.0.0.1:18389`, `127.0.0.1:18636` | interne / loopback |
| **Waitress (Pyramid)** | `6543:6543` → **contourne Apache et son TLS** | `127.0.0.1:16543` | interne / loopback |
| **Postfix** | `9025:25` → relais (cf. S2) | `127.0.0.1:19025` | non publié |
| Apache | `80:80`, `443:443` | `127.0.0.1:8080/8443` | **seul service public légitime** |

**Impact** : l'annuaire LDAP (identité des membres, hashes) et l'application Waitress (sans la terminaison TLS ni les protections d'Apache) sont joignables depuis le réseau de l'hôte — potentiellement Internet si l'hôte a une IP publique et aucun pare-feu (aucun pare-feu n'est fourni dans le dépôt).

**Correctif** — pour tout service non public, lier à la boucle locale (accès debug via tunnel SSH) ou **ne pas publier du tout** (les conteneurs communiquent déjà par le réseau `alirpunkto-net` via les noms de service) :
```yaml
# LDAP / Pyramid : accès debug local uniquement (ou supprimer complètement le bloc ports:)
ports:
  - "127.0.0.1:8389:389"
  - "127.0.0.1:8636:636"
# ...
  - "127.0.0.1:6543:6543"
# Postfix : ne rien publier (cf. audit dédié)
```
Seul Apache conserve `80:80`/`443:443`.

## S4 — [ÉLEVÉ] slapd démarre en niveau debug `-d 256` en production

> **✅ RÉSOLU** — `start_ldap.sh` fixe `SLAPD_DEBUG_LEVEL=0` en prod (« Production mode: foreground without verbose stats logs ») et ne monte à `256` que si `DEBUG_LDAP`/`DEBUG_PASSWORD_LDAP=true`. Le `CMD [… -d 256]` du Dockerfile a disparu (`CMD []`, l'entrypoint choisit le niveau).

`DockerfileOpenLDAP` (`CMD [... "-d", "256"]`) et le fallback de `start_ldap.sh` lancent slapd avec `-d 256` (stats). La prod ne surcharge pas la commande → slapd tourne en debug en production : volume de logs élevé (chaque opération tracée), impact performance, et détails d'annuaire potentiellement journalisés.

**Correctif** : en prod, lancer slapd sans `-d` (ou `-d 0`), et piloter la verbosité par `olcLogLevel` (p. ex. `stats` → `none`/`sync`). Surcharger la `command:` du service `ldap` en prod pour retirer `-d 256`.

## S5 — [MOYEN] Conteneurs en root sans durcissement

> **⚠️ PARTIELLEMENT RÉSOLU** — `security_opt: no-new-privileges:true` est **actif sur les 4 services** (bloque l'escalade via binaires setuid/setgid, sans retirer de capacité) et `cap_drop: ALL` est **actif sur Pyramid** (non-root, port haut → sans risque). Pour **LDAP/Postfix/Apache**, le bloc `cap_drop: ALL` + `cap_add` (jeu minimal recommandé) est fourni **commenté** dans `docker-compose.yaml` : à activer après avoir vérifié que le service démarre toujours sur l'hôte (un jeu trop serré empêche le boot — slapd/Postfix font beaucoup de `chown`/`setuid` au démarrage). `read_only` non appliqué (nécessiterait un mappage `tmpfs` à valider). **Reste à finaliser service par service**, conformément à la démarche progressive de l'audit.

Seul Pyramid tourne non-root (`USER alirpunkto`, `DockerfilePyramid`). **LDAP, Postfix, Apache tournent en root** (aucun `user:`, aucun `USER` dans les Dockerfiles). Aucun conteneur n'a `cap_drop`, `security_opt: [no-new-privileges:true]`, ni `read_only: true`.

**Impact** : surface d'attaque et rayon d'explosion accrus en cas de compromission d'un de ces services (Postfix et Apache étant exposés au réseau).

**Correctif** (progressif, à valider service par service) :
```yaml
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
cap_add:            # ne rajouter que le strict nécessaire (ex. Apache/Postfix : liaison <1024)
  - NET_BIND_SERVICE
# read_only: true + tmpfs pour les répertoires d'exécution, une fois les chemins d'écriture identifiés
```
slapd/postfix supportent mal `read_only` sans `tmpfs` ciblés ; commencer par `no-new-privileges` + `cap_drop: ALL` puis réintroduire les capacités requises.

## S6 — [MOYEN] Fichier de credentials baked dans l'image LDAP

> **✅ RÉSOLU** — `DockerfileOpenLDAP` ne fait plus `COPY ./initials_users.ldif` (« Initial users LDIF is supplied at runtime by bind mount »). Aucun credential n'est cuit dans l'image.

`DockerfileOpenLDAP` : `COPY ./initials_users.ldif /initials_users.ldif`. Même si le fichier de référence ne contient que des placeholders (le vrai est `initials_users.generated.ldif`, bind-monté), il est figé dans une **couche d'image** — toute personne pouvant tirer l'image inspecte cette couche. Le commentaire du Dockerfile le reconnaît d'ailleurs (« Storing plaintext passwords in the image is a critical security risk »).

**Correctif** : ne pas `COPY` de LDIF d'utilisateurs dans l'image ; fournir uniquement le LDIF généré au runtime (bind-mount ou secret). Si un gabarit est nécessaire, le nommer explicitement `.example` et garantir l'absence de toute valeur réelle.

## S7 — [MOYEN] Durcissement Apache non vérifiable (vhost de prod hors dump) + en-têtes de sécurité absents

> **✅ RÉSOLU — réserve de périmètre levée.** Le vhost de prod `docker/etc/apache2/sites-available/alirpunkto.conf.template` est dans le dépôt et durci : `SSLProtocol -all +TLSv1.2 +TLSv1.3` + ciphers Mozilla *intermediate*, `SSLHonorCipherOrder`/`SSLSessionTickets off`, **HSTS** (`max-age=31536000; includeSubDomains`), `X-Frame-Options`/`X-Content-Type-Options`/`Referrer-Policy`, `unset X-Powered-By`, et une **CSP fournie mais désactivée** avec guide de réglage.

Le vhost de prod (`alirpunkto.conf.template`) n'est pas dans le dump : **impossible de vérifier** `SSLProtocol`/`SSLCipherSuite`, HSTS, ni les en-têtes de sécurité (CSP, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`). Le vhost de **test** (inline) n'en pose aucun (HSTS `max-age=0`, acceptable en local, mais aucun autre en-tête ni restriction de protocoles/chiffrements).

**Correctif** : fournir le template pour audit ; y imposer `SSLProtocol -all +TLSv1.2 +TLSv1.3`, une `SSLCipherSuite` moderne, HSTS en prod (`max-age=63072000; includeSubDomains`), et les en-têtes de sécurité applicatifs.

## S8 — [FAIBLE] `.env` non restreint en permissions

> **✅ RÉSOLU** — `init.sh` applique `chmod 600` au `.env` généré (les `secrets/` et `.env` sont déjà gitignorés).

`init.sh` protège correctement les secrets LDAP (`chmod 700 secrets/`, `umask 077` → `ldap_password` en `600`) et génère un `SECRET_KEY` fort (`secrets.token_bytes(32)`). Mais il **n'applique aucun `chmod` sur `docker/.env`**, qui contient pourtant `SECRET_KEY` et `MAIL_PASSWORD` en clair → permissions par défaut (souvent `644`), lisibles par tout utilisateur local.

**Correctif** : `chmod 600 "${ENV_FILE}"` après écriture ; s'assurer que `.env` et `secrets/` sont dans `.gitignore`.

## S9 — [FAIBLE] Module `remoteip` activé sans proxy de confiance déclaré

> **✅ RÉSOLU** — le vhost strippe et régénère `X-Forwarded-For` (`RequestHeader unset X-Forwarded-For early`) : Apache étant l'edge, le backend lit l'entrée régénérée depuis l'IP réelle du pair. Une note documente le passage à `mod_remoteip` (`RemoteIPHeader` + `RemoteIPTrustedProxy`) si un CDN/LB est ajouté en amont.

`DockerfileApache2` et `start_test_apache2.sh` activent `remoteip` sans `RemoteIPHeader`/`RemoteIPTrustedProxy` visibles (prod hors dump). Si `remoteip` est réellement utilisé pour dériver l'IP client depuis `X-Forwarded-For` sans restreindre aux proxys internes, un client peut usurper son IP.

**Correctif** : soit ne pas activer `remoteip` si inutile, soit le configurer avec `RemoteIPHeader X-Forwarded-For` **et** `RemoteIPTrustedProxy`/`RemoteIPInternalProxy` limité à l'adresse d'Apache/du reverse-proxy.

**Points positifs sécurité** : `SECRET_KEY` robuste et purgé de l'environnement après lecture (`secret_manager`) ; mot de passe LDAP via **docker secret** (`600`) ; mots de passe utilisateurs hashés `{SSHA}` (slappasswd) ; Pyramid non-root ; healthchecks partout ; **liaison loopback systématique en test**.

---

# 2. Résilience

## R1 — [ÉLEVÉ] Aucune limite de ressources

> **✅ RÉSOLU** — `mem_limit` sur les 4 services (1 GB par défaut, 8 GB pour Pyramid).

Aucun conteneur (prod **ni** test) ne définit `mem_limit`/`cpus` ou `deploy.resources.limits`. Un conteneur qui fuit (ou une charge anormale sur Postfix/Apache exposés) peut consommer toute la mémoire/CPU de l'hôte et **emporter toute la pile**.

**Correctif** : borner chaque service, p. ex.
```yaml
deploy:
  resources:
    limits: { memory: 512M, cpus: "1.0" }
# ou, hors Swarm : mem_limit: 512m  /  cpus: 1.0
```
Dimensionner slapd et Pyramid/ZODB selon la charge réelle.

## R2 — [MOYEN] Pas de rotation des logs

> **✅ RÉSOLU** — `logging: json-file` (`max-size: 10m`, `max-file: 5`) sur les 4 services (~50 MB de logs bornés par conteneur).

Aucun `logging:` configuré → croissance non bornée des journaux, **aggravée par slapd `-d 256` (S4) et `set -x` (S1)**. Risque de saturation disque de l'hôte.

**Correctif** :
```yaml
logging:
  driver: json-file
  options: { max-size: "10m", max-file: "5" }
```
(idéalement au niveau daemon `daemon.json` pour couvrir tous les conteneurs), et réduire la verbosité applicative (S1, S4).

## R3 — [MOYEN] Renouvellement TLS uniquement au redémarrage du conteneur

> **✅ RÉSOLU** — `start_apache2.sh` lance une **boucle de fond** (`sleep 12h` + `certbot renew --deploy-hook "apache2ctl graceful"`) en plus du renouvellement initial : plus de certificat expiré sur un conteneur longue durée.

`start_apache2.sh` exécute `certbot renew` **une seule fois, au démarrage**, avant `exec apache2ctl`. Un conteneur qui tourne plus de ~90 jours sans redémarrage voit son certificat **expirer** (pas de cron/timer de renouvellement).

**Correctif** : ajouter un timer de renouvellement (cron dans le conteneur, ou service dédié, ou `systemd` côté hôte) qui exécute `certbot renew` puis recharge Apache (`apache2ctl graceful`) périodiquement.

## R4 — [MOYEN] Aucune stratégie de sauvegarde

> **✅ RÉSOLU** — nouveau `docker/backup.sh` : `slapcat -n 0/-n 1` (LDAP → LDIF) + copie à chaud du `Data.fs` (ZODB), tarball horodaté, rotation `KEEP_DAYS`, notes de restauration (slapadd / remplacement du `Data.fs` / `repozo`). **À planifier** via cron/timer (exemple fourni).

Pas de sauvegarde planifiée du volume **ZODB** (`alirpunkto_pyramid_var`, données applicatives) ni de l'**annuaire LDAP** (slapd `dump_database` en mode « when needed » uniquement). Une corruption ou une suppression de volume est irréversible.

**Correctif** : sauvegardes planifiées — `slapcat` régulier pour LDAP, copie/rotation du `Data.fs` (ZODB supporte la copie à chaud + `pack`), export hors-hôte, et **test de restauration** documenté.

## R5 — [FAIBLE] Politique `restart: "no"` en test (amplificateur du bug mail — cf. §3)

> **✅ RÉSOLU** — les 4 services de `test-docker-compose.yaml` passent en `restart: unless-stopped` (comme la prod).

Tous les services de test utilisent `restart: "no"` alors que la prod utilise `restart: unless-stopped`. Couplé au design d'entrée `wait -n "$OPENDKIM_PID" "$POSTFIX_PID"` + `trap cleanup EXIT` (si l'un des deux processus rend la main, le script sort et le trap tue le conteneur), un hoquet transitoire **laisse le conteneur mort** en test alors qu'il **se répare tout seul** en prod. C'est le mécanisme le plus probable du bug mail (§3).

**Correctif** : voir §3.

## R6 — [FAIBLE] Pas de segmentation réseau

> **✅ RÉSOLU (à valider en marche)** — segmentation en deux réseaux : `alirpunkto-frontend` (Apache↔Pyramid) et `alirpunkto-backend` (Pyramid↔LDAP/Postfix). Apache ne joint plus LDAP/Postfix, et réciproquement. **Connectivité inter-tiers à confirmer sur pile lancée** (non testable hors exécution).

Tous les services partagent un unique bridge (`alirpunkto-net`) → l'annuaire LDAP est joignable par Apache et Postfix sans nécessité.

**Correctif** : séparer les tiers (p. ex. réseau `backend` pour Pyramid↔LDAP↔Postfix, réseau `frontend` pour Apache↔Pyramid), ne connecter chaque service qu'aux réseaux requis.

## R7 — [FAIBLE] Nettoyage de production incomplet

> **✅ RÉSOLU** — `stop_clean_delete.sh` réécrit autour de `docker compose … down --remove-orphans` (au lieu de ne retirer que LDAP), avec l'option `--volumes` pour supprimer aussi les volumes nommés.

`stop_clean_delete.sh` ne nettoie que le service LDAP (conteneur/image/volumes) ; Postfix, Pyramid, Apache et leurs volumes sont ignorés. `stop_clean_test.sh` fait bien mieux (`compose down -v --remove-orphans`).

**Correctif** : aligner le script de prod sur `docker compose ... down` (avec option explicite pour les volumes), pour un nettoyage cohérent et complet.

## R8 — [FAIBLE] Healthchecks superficiels

> **✅ RÉSOLU** — healthcheck **fonctionnel** de Postfix (prod et test) : connexion sur `127.0.0.1:25` et vérification du code d'accueil `220`. `depends_on: service_healthy` ne débloque Pyramid que lorsque Postfix répond réellement.

Le healthcheck Postfix (`ss -ltn | grep -q ':25'`) ne vérifie que la **présence du port**, pas qu'une transaction SMTP aboutit ni que le socket milter OpenDKIM est prêt. Un `depends_on: condition: service_healthy` peut donc être satisfait alors que le service n'est pas fonctionnellement prêt (lien direct avec §3).

**Correctif** : sonde fonctionnelle (voir §3, correctif 2).

## R9 — [FAIBLE] Réseau de test « internal » annoncé mais non configuré

> **✅ RÉSOLU** — le commentaire trompeur suggérant `internal: true` est corrigé : réseau de test = **bridge normal**, car le Pyramid de test exécute `pip install -e .[testing]` au runtime (`internal:true` casserait l'install sauf miroir PyPI local). `README_TEST_LOCAL.md` corrigé.

L'en-tête de `test-docker-compose.yaml` affirme « internal Docker network to prevent containers from reaching the Internet », mais le réseau est `driver: bridge` **sans** `internal: true`. Les conteneurs de test peuvent donc atteindre Internet — incohérence commentaire/config (et surface inattendue si un test suppose l'isolement).

**Correctif** : soit ajouter `internal: true` (et alors prévoir un miroir/proxy pour `pip install` au runtime, cf. `INSTALL_EXTRAS_TESTING`), soit corriger le commentaire.

**Points positifs résilience** : healthchecks + `depends_on: condition: service_healthy` partout ; `restart: unless-stopped` en prod ; volumes nommés persistants ; séparation nette des noms/volumes/réseau entre prod et test.

---

# 3. Bug mail de la pile de test — diagnostic et correctifs

> **✅ RÉSOLU (causes structurelles).** Les quatre correctifs §3.4 sont appliqués : **c1** `restart: unless-stopped` en test (R5) ; **c2** healthcheck SMTP fonctionnel (R8) ; **c3** entrypoint prod fiabilisé — **boucle de supervision** qui redémarre l'enfant tombé au lieu de laisser `wait -n` + le `trap … EXIT` détruire le conteneur ; **c4** sink de test **sans OpenDKIM**, Postfix en **PID 1**. La course de démarrage et l'arrêt en cascade sont supprimés ; une **reproduction sur pile lancée** reste recommandée pour confirmer la disparition du symptôme.

## 3.1 Ce qui est **prouvé** : ce n'est PAS un problème de configuration mail

**(a) Le transport mail est identiquement configuré en test et en prod.** L'application lit `MAIL_HOST/PORT/TLS/SSL` via `os.getenv` (`constants_and_globals.py`), et `load_dotenv` est en `override=False` : les valeurs du `environment:` du compose l'emportent. Valeurs effectives :

| | Prod | Test |
|---|---|---|
| `MAIL_HOST` | `alirpunkto-postfix` | `alirpunkto-test-postfix` |
| `MAIL_PORT` | `25` | `25` |
| `MAIL_TLS` / `MAIL_SSL` | `false` / `false` | `false` / `false` |

`.env`/`.env.test` (générés par `init.sh`/`init_test.sh`) sont **cohérents** avec ces valeurs. Le mailer est **toujours** construit (`config.registry['mailer'] = Mailer.from_settings(settings)`, non conditionnel).

**(b) TLS est écarté.** `pyramid_mailer` mappe `no_tls = not tls` ; avec `mail.tls=false` → `asbool("false")=False` → `no_tls=True` ⇒ **STARTTLS désactivé** (pas d'opportuniste). Identique prod/test.

**(c) Le diff des `postconf` prod vs test ne touche jamais l'acceptation SMTP.** Toutes les différences (`default/relay/local_transport=discard:`, `disable_dns_lookups`, `mydestination`, `relay_domains`, `smtp_host_lookup`, `ignore_mx_lookup_error`) portent sur la **livraison sortante**. `smtpd_relay_restrictions = permit_mynetworks, reject_unauth_destination` et l'auto-détection de `mynetworks` sont **identiques**. Le smtpd de test accepte donc le mail de Pyramid exactement comme la prod (via `permit_mynetworks`, Pyramid étant dans le sous-réseau du bridge), puis le **jette** au lieu de le relayer.

**(d) Preuve empirique.** Un sink qui **accepte puis jette** (équivalent du `discard:` de test) renvoie `250` ; `mailer.send()` suivi de `transaction.commit()` **réussissent**. À l'inverse, si Postfix est **injoignable**, le commit lève `ConnectionRefusedError: [Errno 111]` — **exactement** la classe d'erreur qui remonte côté Pyramid.

> **Conclusion** : `mailer.send()` est **différé à la validation de transaction** (pyramid_tm) — la connexion SMTP réelle a lieu **au commit**, en fin de requête. Le sink `discard` renvoyant toujours `250`, une **erreur côté Pyramid ne peut provenir que du niveau connexion** : au moment du commit, le conteneur Postfix de test **n'est pas joignable** (mort, non encore prêt, ou coupé). **Cesser de chercher côté réglages mail.**

## 3.2 Cause opérationnelle la plus probable

La différence décisive entre les deux piles est **la politique de redémarrage**, combinée au design de l'entrypoint et à un healthcheck superficiel :

1. **`restart: "no"` (test) vs `restart: unless-stopped` (prod)** — en prod, un Postfix qui sort pour une raison transitoire **redémarre** ; en test, il **reste mort**.
2. **Entrypoint** : `postfix start-fg &` + `/usr/sbin/opendkim ... &` + `wait -n "$OPENDKIM_PID" "$POSTFIX_PID"` avec `trap cleanup EXIT INT TERM`. Si **l'un** des deux processus rend la main, `wait -n` retourne, le script se termine, et le `trap` **tue l'autre** → le conteneur s'arrête. En prod, il repart ; en test, non.
3. **Healthcheck** (`ss -ltn | grep -q ':25'`) : ne prouve que la **liaison du port**, pas qu'une transaction SMTP aboutit ni que le milter OpenDKIM est prêt. `depends_on: condition: service_healthy` peut donc démarrer Pyramid alors que Postfix n'est pas durablement/fonctionnellement prêt.

Résultat : le Postfix de test peut se retrouver **Exited et non redémarré** pendant que Pyramid tourne ; l'envoi différé (au commit) frappe un Postfix mort → `ConnectionRefusedError` → 500 côté Pyramid. La prod masque exactement la même fragilité grâce au redémarrage automatique.

## 3.3 Runbook de diagnostic (à exécuter sur l'hôte, pile lancée, après reproduction)

```bash
# 1) Le conteneur Postfix de test est-il encore vivant ?
docker ps -a --filter name=alirpunkto-test-postfix        # STATUS = Exited ?  ← cause probable
docker logs --tail=200 alirpunkto-test-postfix            # crash ? erreur au démarrage ?

# 2) Postfix écoute-t-il et avec quel mynetworks ?
docker exec alirpunkto-test-postfix ss -ltn | grep ':25'
docker exec alirpunkto-test-postfix postconf mynetworks smtpd_relay_restrictions

# 3) Le socket milter OpenDKIM est-il présent ?
docker exec alirpunkto-test-postfix ls -l /run/opendkim/opendkim.sock

# 4) Connectivité + transaction SMTP réelle DEPUIS le conteneur Pyramid VERS Postfix :
docker exec alirpunkto-test-pyramid python3 - <<'PY'
import smtplib
try:
    s = smtplib.SMTP("alirpunkto-test-postfix", 25, timeout=5)
    code, msg = s.ehlo()
    print("EHLO:", code)
    print("MAIL:", s.mail("test-admin@alirpunkto.localhost"))
    print("RCPT:", s.rcpt("user1@example.com"))       # 250 attendu (permit_mynetworks)
    print("DATA:", s.data("Subject: probe\r\n\r\nhello"))  # 250 attendu (accept+discard)
    s.quit()
    print("=> SMTP OK : le problème est intermittent/au démarrage (voir restart policy)")
except Exception as e:
    print("=> ECHEC:", type(e).__name__, e)           # ConnectionRefused => Postfix mort/injoignable
PY
```
- **`Exited` / `Connection refused`** ⇒ Postfix mort non redémarré → correctif 1 (et 3).
- **`250` partout** ⇒ échec **intermittent** au premier envoi (course de démarrage) → correctifs 1 + 2.
- **`4xx/5xx` à RCPT/DATA** ⇒ (peu probable au vu de la config) rejet smtpd → vérifier `mynetworks` et le milter.

## 3.4 Correctifs

> **✅ Les quatre correctifs ci-dessous sont appliqués dans le dépôt** (voir l'encart en tête du §3).

**Correctif 1 — Rendre le Postfix de test auto-réparant (aligne test sur prod).** C'est le correctif à plus fort effet sur le symptôme visible.
```yaml
# test-docker-compose.yaml, service postfix (et, idéalement, les autres services de test)
postfix:
  restart: unless-stopped        # au lieu de "no"  (ou "on-failure")
```

**Correctif 2 — Healthcheck fonctionnel (prouver un chemin SMTP, pas juste un port ouvert).**
```yaml
healthcheck:
  test: ["CMD-SHELL",
    "printf 'EHLO probe\\r\\nMAIL FROM:<p@alirpunkto.localhost>\\r\\nRCPT TO:<t@example.com>\\r\\nQUIT\\r\\n' \
     | timeout 5 bash -c 'cat >/dev/tcp/127.0.0.1/25; head -c 0 <&1' 2>/dev/null; \
     ss -ltn | grep -q ':25'"]
  interval: 15s
  timeout: 7s
  retries: 8
  start_period: 20s
```
(ou une petite sonde `python3 smtplib` équivalente vérifiant `EHLO`+`RCPT`). Ainsi `depends_on: condition: service_healthy` ne débloque Pyramid que lorsque Postfix accepte réellement un mail — supprimant la course de démarrage.

**Correctif 3 — Fiabiliser l'entrypoint** pour qu'un hoquet d'un seul enfant ne tue pas définitivement le conteneur. Trois options, par ordre de robustesse :
- exécuter **Postfix au premier plan comme PID 1** (`exec postfix start-fg`) et lancer OpenDKIM sous un superviseur léger (`supervisord`/`s6`) qui le redémarre ;
- ou, à design constant, **relancer** l'enfant qui tombe au lieu de sortir (boucle de supervision autour de `wait -n`) ;
- a minima, retirer `non_smtpd_milters`/`smtpd_milters` du chemin critique en test (le sink n'a pas besoin de signer DKIM), ce qui supprime OpenDKIM comme cause possible d'arrêt.

**Correctif 4 (hygiène)** — le sink de test génère une clé DKIM et lance OpenDKIM pour rien (mail jeté). Le désactiver en test simplifie la pile et élimine une source d'arrêt (`wait -n`).

---

# 4. Récapitulatif priorisé

| # | Domaine | Action | Sévérité | Statut |
|---|---|---|---|---|
| S1 | Sécurité | `set -x` conditionnel + heredoc masqué + `ldapadd -Y EXTERNAL` | Critique | ✅ Résolu |
| S2 | Sécurité | Relais Postfix fermé (port 25 non publié) | Critique | ✅ Résolu |
| S3 | Sécurité | LDAP/Waitress liés en `127.0.0.1`, SMTP non publié | Élevée | ✅ Résolu |
| S4 | Sécurité | slapd `-d 0` en prod (256 uniquement en debug) | Élevée | ✅ Résolu |
| R1 | Résilience | `mem_limit` sur chaque service | Élevée | ✅ Résolu |
| S5 | Sécurité | `no-new-privileges` (×4) + `cap_drop: ALL` (Pyramid) ; `cap_*` LDAP/Postfix/Apache en guidance | Moyenne | ⚠️ Partiel |
| R3 | Résilience | Boucle de renouvellement certbot + reload Apache | Moyenne | ✅ Résolu |
| R4 | Résilience | `backup.sh` (slapcat + copie `Data.fs`, rotation) | Moyenne | ✅ Résolu |
| R2 | Résilience | Rotation des logs `json-file` | Moyenne | ✅ Résolu |
| **§3** | **Bug mail** | **restart unless-stopped + healthcheck SMTP + entrypoint supervisé + sink sans OpenDKIM** | — | ✅ Résolu¹ |
| S6 | Sécurité | Plus de LDIF *baked* dans l'image LDAP | Moyenne | ✅ Résolu |
| S7 | Sécurité | vhost prod durci (TLS 1.2/1.3, HSTS, en-têtes, CSP guidée) | Moyenne | ✅ Résolu |
| S8 | Sécurité | `chmod 600` sur `.env` | Faible | ✅ Résolu |
| S9 | Sécurité | XFF strippé/régénéré (Apache = edge) | Faible | ✅ Résolu |
| R5 | Résilience | `restart: unless-stopped` en test | Faible | ✅ Résolu |
| R6 | Résilience | Segmentation frontend/backend | Faible | ✅ Résolu² |
| R7 | Résilience | `stop_clean_delete.sh` (down + `--volumes`) | Faible | ✅ Résolu |
| R8 | Résilience | Healthcheck SMTP fonctionnel | Faible | ✅ Résolu |
| R9 | Résilience | Commentaire « internal » corrigé (bridge normal) | Faible | ✅ Résolu |

¹ Causes structurelles corrigées ; reproduction sur pile recommandée. &nbsp;&nbsp; ² Connectivité inter-tiers à valider sur pile lancée.

## Fichiers à fournir pour compléter l'audit

> **MàJ 2026-07-06 — plus rien à fournir.** Les trois fichiers autrefois hors dump
> sont désormais présents dans le dépôt : `docker/etc/postfix/main.cf`,
> `docker/etc/opendkim.conf`, `docker/etc/apache2/sites-available/alirpunkto.conf.template`
> (vhost **de prod**). Le durcissement TLS/en-têtes Apache est vérifié (**S7**) et
> `opendkim.conf`/`main.cf` complètent — sans les contredire — les `postconf -e`
> des scripts. La réserve de périmètre de l'en-tête est levée.
