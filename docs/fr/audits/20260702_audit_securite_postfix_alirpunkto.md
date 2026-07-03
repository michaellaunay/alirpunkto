# Audit de sécurité — conteneur Postfix AlirPunkto

> **Contexte** : IP mise en liste noire après signalement. **Périmètre** : `docker/DockerfilePostfix`, `docker/start_postfix.sh`, `docker/start_test_postfix.sh`, `docker/docker-compose.yaml`, `docker/test-docker-compose.yaml`, `docker/README.md`, `docker/init.sh`.
> **Réserve de périmètre** : `docker/etc/postfix/main.cf` et `docker/etc/opendkim.conf` sont copiés dans l'image (`COPY` dans le Dockerfile) mais **absents du dump** (le script d'export ne prend, sous `docker/`, que `Dockerfile*`, `*.yaml/yml`, `*.sh`, `README*.md`). Les réglages de relais effectifs sont toutefois **tous** posés à l'exécution par `postconf -e` dans `start_postfix.sh`, donc l'analyse du relais est complète ; seuls d'éventuels réglages additionnels de `main.cf` et le **mode** d'OpenDKIM n'ont pas pu être relus (voir §D et §H).

---

## Verdict

**Oui — dans la configuration Docker par défaut, ce conteneur est un relais ouvert exploitable depuis Internet.** Le blacklistage est cohérent avec une exploitation en relais de spam. Trois défauts se combinent ; aucun n'est suffisant seul, mais **réunis ils ouvrent le relais au monde entier**, et deux d'entre eux sont dans l'état par défaut livré.

La bonne nouvelle : la pile de **test** est correctement bâtie (port lié à `127.0.0.1`, livraison externe coupée). C'est **uniquement la pile de production** qui est vulnérable, ce qui rend le correctif ciblé.

---

## Le mécanisme (chaîne d'exploitation)

### A. Le port 25 est publié sur toutes les interfaces de l'hôte
`docker/docker-compose.yaml` (service `postfix`) :
```yaml
ports:
  - "9025:25"      # = 0.0.0.0:9025 → exposé sur TOUTES les interfaces, dont l'IP publique
```
Idem dans le README (`docker run ... -p 9025:25`). À comparer avec la pile de test, qui fait ce qu'il faut :
```yaml
# test-docker-compose.yaml
- "127.0.0.1:19025:25"   # lié à la boucle locale uniquement → inaccessible de l'extérieur
```
Aucune règle de pare-feu hôte n'est fournie ni documentée (aucun `ufw`/`iptables`/`nftables`/`daemon.json` dans le dépôt). Donc, sauf pare-feu externe, **n'importe qui sur Internet peut ouvrir une session SMTP sur `<ip_publique>:9025`**.

> Or Postfix, en send-only pour les notifications de l'application, **n'a aucun besoin d'un port publié** : Pyramid le joint par le réseau interne `alirpunkto-net` via le nom de service `alirpunkto-postfix:25`. La publication de port n'apporte rien et ouvre la surface d'attaque.

### B. `mynetworks` fait confiance à TOUT le sous-réseau du bridge (et n'est jamais borné)
`start_postfix.sh` calcule `mynetworks` par auto-détection dès que `POSTFIX_MYNETWORKS` est vide — et cette variable **n'est définie nulle part** (ni dans le `environment:` du compose, ni dans le `.env` généré par `init.sh`). L'auto-détection tourne donc **toujours** :
```bash
NETWORK="$(ip -o -f inet route show dev eth0 | awk '$1 != "default" {print $1; exit}')"
postconf -e "mynetworks = 127.0.0.0/8 ${NETWORK}"
```
Sur un bridge Docker Compose typique, `NETWORK` vaut `172.18.0.0/16` (un **/16 = 65 000 adresses**). Résultat effectif :
```
mynetworks = 127.0.0.0/8 172.18.0.0/16
```
Combiné à la règle de relais :
```bash
smtpd_relay_restrictions = permit_mynetworks, reject_unauth_destination
```
`permit_mynetworks` est évalué **en premier** : toute connexion dont l'IP source tombe dans `172.18.0.0/16` est autorisée à relayer vers n'importe quelle destination, **court-circuitant** `reject_unauth_destination`. La protection standard anti-relais est donc neutralisée par un périmètre de confiance beaucoup trop large.

### C. Le NAT Docker fait entrer le trafic Internet *dans* le périmètre de confiance
Avec l'**userland-proxy** de Docker (activé par défaut), une connexion arrivant sur le port publié est réémise vers le conteneur avec pour **IP source la passerelle du bridge** (p. ex. `172.18.0.1`). Or cette passerelle est **dans** le sous-réseau auto-détecté :

| Sous-réseau bridge | `mynetworks` calculé | Passerelle (= source vue par Postfix) | ∈ mynetworks ? |
|---|---|---|---|
| `172.18.0.0/16` | `127.0.0.0/8 172.18.0.0/16` | `172.18.0.1` | **OUI** |
| `172.19.0.0/16` | `127.0.0.0/8 172.19.0.0/16` | `172.19.0.1` | **OUI** |
| `10.5.0.0/24` | `127.0.0.0/8 10.5.0.0/24` | `10.5.0.1` | **OUI** |

Donc : un spammeur sur Internet → `<ip_publique>:9025` → réémis depuis `172.18.0.1` → **Postfix le voit comme membre de `mynetworks`** → `permit_mynetworks` → **relais accepté**. **Relais ouvert planétaire.**

> Nuance honnête : avec `userland-proxy: false` (DNAT iptables/nftables pur), l'IP publique réelle du client est généralement **préservée**, et un spammeur externe serait alors bloqué par `reject_unauth_destination`. Mais (1) l'userland-proxy est le **défaut** de Docker ; (2) même sans lui, **tout conteneur ou hôte présent sur le bridge** relaie librement, et le `/16` de confiance reste une bombe à retardement ; (3) dépendre de ce détail non maîtrisé n'est pas défendable. Ton IP ayant *réellement* été blacklistée, tu as très probablement rencontré exactement ce chemin (userland-proxy actif).

---

## Correctifs

### 1. Endiguement immédiat (arrêter l'hémorragie maintenant)

Sur l'hôte, dans le conteneur Postfix — resserrer `mynetworks` à la boucle locale et recharger :
```bash
docker exec alirpunkto-postfix postconf -e 'mynetworks = 127.0.0.0/8 [::1]/128'
docker exec alirpunkto-postfix postconf mynetworks          # vérifier
docker exec alirpunkto-postfix postfix reload
```
> Effet de bord : Pyramid relaie aujourd'hui *parce qu'il est dans le sous-réseau*. Après ce resserrage, le mail applicatif **cessera** tant que tu n'auras pas rétabli une autorisation propre (IP fixe du conteneur ou SASL, §2). C'est le bon compromis : couper le spam prime, quitte à suspendre brièvement les notifications.

Et couper l'accès Internet au port dans la foulée — éditer `docker/docker-compose.yaml` pour **supprimer** la publication (ou au minimum la lier à la boucle locale), puis :
```bash
docker compose --env-file docker/.env -f docker/docker-compose.yaml up -d postfix
```

Purger la file de tout spam en attente (voir §Post-incident) **avant** de rouvrir quoi que ce soit.

### 2. Correctif durable (topologie propre)

**2.a — Ne pas publier le port 25.** Postfix est joignable par Pyramid via `alirpunkto-net`. Supprimer purement le mapping :
```diff
   postfix:
     ...
     networks:
       - alirpunkto-net
-    ports:
-      - "9025:25"
```
À ne conserver **que** si l'hôte doit vraiment être un MX entrant Internet — auquel cas : lier explicitement (`"<ip_publique>:25:25"`), pare-feu hôte, et appliquer impérativement 2.b + 2.c. Pour un usage send-only, la suppression est la bonne réponse et **elle élimine à elle seule le vecteur des §A et §C**.

**2.b — Borner `mynetworks` et ne plus jamais auto-détecter.** Fixer la variable explicitement pour désactiver le bloc `awk` :
```yaml
  postfix:
    environment:
      DOMAIN: ${DOMAIN}
      POSTFIX_MYHOSTNAME: ${POSTFIX_MYHOSTNAME}
      POSTFIX_MYNETWORKS: "127.0.0.0/8 [::1]/128"   # ← ne JAMAIS laisser vide
```
Comme Pyramid ne sera plus « dans le sous-réseau », l'autoriser **nominativement**. Deux options :

- **Option simple — IP fixe du conteneur applicatif** (pas de SASL) : donner à Pyramid une IP statique sur le réseau et ne faire confiance qu'à elle.
  ```yaml
  networks:
    alirpunkto-net:
      name: alirpunkto-net
      driver: bridge
      ipam:
        config:
          - subnet: 172.28.0.0/24
  services:
    pyramid:
      networks:
        alirpunkto-net:
          ipv4_address: 172.28.0.10
    postfix:
      environment:
        POSTFIX_MYNETWORKS: "127.0.0.0/8 [::1]/128 172.28.0.10/32"   # ← seul Pyramid
  ```
  Confiance limitée à **une** adresse (`/32`) au lieu de 65 000.

- **Option robuste — authentification SASL** (recommandée ; `init.sh` collecte déjà `MAIL_USERNAME`/`MAIL_PASSWORD`, aujourd'hui inutilisés côté smtpd). Exiger l'auth et retirer la confiance par IP :
  ```bash
  smtpd_sasl_auth_enable = yes
  smtpd_sasl_type = dovecot           # ou cyrus/saslauthd selon l'implémentation retenue
  smtpd_tls_security_level = may      # au minimum ; encrypt si port dédié submission
  smtpd_relay_restrictions = permit_sasl_authenticated, reject_unauth_destination
  # permit_mynetworks retiré ; mynetworks réduit à la boucle locale
  ```
  Côté Pyramid, renseigner `mail.username`/`mail.password`/`mail.tls` dans `production.ini`. C'est la seule option qui reste sûre quel que soit le comportement de NAT.

**2.c — Restrictions SMTP explicites + limitation de débit** (défense en profondeur, borne l'abus même en cas de brèche future) :
```bash
smtpd_helo_required = yes
smtpd_helo_restrictions          = permit_mynetworks, permit_sasl_authenticated, reject_invalid_helo_hostname, reject_non_fqdn_helo_hostname
smtpd_sender_restrictions        = permit_mynetworks, permit_sasl_authenticated, reject_non_fqdn_sender, reject_unknown_sender_domain
smtpd_recipient_restrictions     = permit_mynetworks, permit_sasl_authenticated, reject_non_fqdn_recipient, reject_unauth_destination
# Anti-abus (anvil) :
smtpd_client_connection_rate_limit  = 30
smtpd_client_message_rate_limit     = 100
anvil_rate_time_unit                = 60s
```

**2.d — Corriger le défaut dans le script** pour qu'un `mynetworks` vide ne retombe **jamais** sur le sous-réseau entier. Remplacer le bloc `else` d'auto-détection par une valeur sûre :
```bash
if [ -n "${POSTFIX_MYNETWORKS}" ]; then
    postconf -e "mynetworks = ${POSTFIX_MYNETWORKS}"
else
    # Défaut SÛR : ne jamais faire confiance à tout le sous-réseau du bridge.
    postconf -e "mynetworks = 127.0.0.0/8 [::1]/128"
fi
```
(Le même bloc `awk` est présent dans `start_test_postfix.sh` ; l'y corriger aussi par cohérence, même si la pile de test n'expose pas le port.)

---

## Après remise en état : vérifier que le relais est bien fermé

Depuis une machine **externe** (test de relais ouvert) :
```bash
swaks --server <ip_publique>:9025 --from spammer@evil.example --to cible@gmail.com
# Attendu APRÈS correctif : 554 5.7.1 <cible@gmail.com>: Relay access denied
# AVANT correctif : 250 Ok  ← relais ouvert
```
Depuis l'hôte (état effectif) :
```bash
docker exec alirpunkto-postfix postconf mynetworks smtpd_relay_restrictions inet_interfaces
docker exec alirpunkto-postfix ss -ltnp | grep ':25'   # le port ne doit PAS être exposé publiquement
```

---

## Post-incident (nettoyage & délistage)

1. **Inspecter la file** pour des traces d'abus (destinataires étrangers, gros volumes) :
   ```bash
   docker exec alirpunkto-postfix postqueue -p | tail -50
   docker exec alirpunkto-postfix sh -c 'grep "relay=" /var/log/mail.log | tail -100'
   ```
2. **Purger le spam en attente** (si file compromise) :
   ```bash
   docker exec alirpunkto-postfix postsuper -d ALL           # vide TOUTE la file — vérifier d'abord qu'aucun mail légitime n'y est
   ```
3. **Délistage** : une fois le relais fermé et la file assainie, demander le retrait auprès des RBL concernées (Spamhaus, Barracuda, SORBS, etc. — l'e-mail reçu indique souvent laquelle). Ne pas demander le délistage **avant** d'avoir fermé le relais : un re-listing immédiat aggrave la réputation.
4. **Réputation domaine** : vérifier §H — si OpenDKIM a signé le spam, c'est la réputation du **domaine** (pas seulement l'IP) qui est atteinte. Publier/valider SPF et DMARC (voir §H).

---

## Constats secondaires (à traiter après l'urgence)

### D. Fichiers de base non audités (réserve)
`main.cf` et `opendkim.conf` copiés dans l'image mais hors dump. Les réglages de relais sont intégralement pilotés par `postconf -e` (donc couverts), mais `main.cf` pourrait porter d'autres directives et `opendkim.conf` détermine le **mode** d'OpenDKIM (§H). À fournir pour une revue complète.

### E. `inet_interfaces = all`
Cohérent avec un port publié, mais inutile en send-only via réseau interne. Si le port 25 n'est plus publié (2.a), envisager de restreindre l'écoute. Sans grand risque une fois `mynetworks` borné, mais réduit la surface.

### F. OpenDKIM signe `*@${DOMAIN}` — risque de signature du spam
`SigningTable` = `*@${DOMAIN}`. Si le relais est ouvert **et** qu'un spammeur émet en `From: *@${DOMAIN}`, OpenDKIM appose une **signature DKIM valide** du domaine sur le spam → dégât de réputation **du domaine**, pas seulement de l'IP. La fermeture du relais (§2) élimine la cause ; en complément, cadrer `InternalHosts`/`ExternalIgnoreList` d'OpenDKIM pour ne signer que le trafic réellement interne (à vérifier dans `opendkim.conf`, absent du dump).

### G. `MAIL_USERNAME`/`MAIL_PASSWORD` collectés mais non appliqués côté smtpd
`init.sh` demande des identifiants SMTP, mais le smtpd Postfix n'active pas SASL (`smtpd_sasl_auth_enable` absent) : ces identifiants ne servent aujourd'hui qu'à s'authentifier auprès d'un `relayhost` amont. Les réutiliser pour l'option SASL (2.b) referme proprement le relais.

### H. SPF / DMARC / rDNS — hygiène anti-spam et réputation
Le README documente uniquement le TXT DKIM. Pour émettre sans être classé spam et limiter l'usurpation :
- **SPF** : publier un TXT `v=spf1 ... -all` autorisant l'IP émettrice.
- **DMARC** : publier `_dmarc.<domaine>` (`v=DMARC1; p=quarantine; rua=...`).
- **rDNS/PTR** cohérent avec `myhostname`, et FCrDNS (PTR ↔ A) — souvent exigé par les grands fournisseurs.
Documenter ces trois points à côté du DKIM dans le README.

### I. `relay_domains = ${DOMAIN}` sans transport dédié
Postfix accepte le courrier entrant `@${DOMAIN}` (rôle MX) alors que `mydestination = localhost` et qu'aucun transport n'est défini pour `${DOMAIN}` → risque de boucle/rebonds si un MX pointe ici. Sans impact sur le relais ouvert, mais à clarifier selon que le conteneur doit ou non recevoir du courrier entrant. En send-only, `relay_domains =` (vide) est plus sûr — c'est d'ailleurs ce que fait la pile de **test**.

---

## Récapitulatif priorisé

| # | Action | Gravité | Effort |
|---|---|---|---|
| 1 | Resserrer `mynetworks` à la boucle locale + retirer la publication du port 25 (endiguement) | **Critique** | 5 min |
| 2 | Purger la file du spam, inspecter les logs, demander le délistage | **Critique** | 30 min |
| 3 | Correctif durable : pas de port publié + `mynetworks` borné + IP fixe **ou** SASL (2.a→2.c) | **Critique** | 1–2 h |
| 4 | Défaut sûr dans `start_postfix.sh`/`start_test_postfix.sh` (plus jamais le sous-réseau entier) | Élevée | 15 min |
| 5 | SPF + DMARC + rDNS ; cadrer OpenDKIM (`InternalHosts`) | Élevée | 1 h |
| 6 | Fournir `main.cf`/`opendkim.conf` pour revue complète ; rate limiting ; `relay_domains` | Moyenne | — |
