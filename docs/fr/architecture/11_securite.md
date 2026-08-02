# Sécurité

> Statut : documentation courante — synthèse ; le détail des constats et
> correctifs est dans `docs/fr/audits/` (revues de code et audits Docker,
> Postfix, 2026).

## Protections applicatives en vigueur

- **CSRF global** : `set_default_csrf_options(require_csrf=True)` — toutes
  les vues sont protégées, les formulaires portent le jeton.
- **Sessions** : cookie signé `httponly`, `secure`, `SameSite=Lax` ; contenu
  minimal, *access token* SSO jamais stocké (budget cookie,
  `tests/test_session_cookie_budget.py`).
- **Mots de passe** : hachés `{SSHA}` à toute écriture LDAP
  (`secret_manager.make_ldap_password`), jamais stockés en clair en ZODB
  (`secure_password_fields`, purge à l'acceptation) — constat 1.3 de la
  revue de code, verrouillé par
  `tests/test_security_1_3_password_hashing.py`. L'outil
  `tools/purge_zodb_cleartext_passwords.py` assainit les bases historiques.
- **Secrets** : lus de l'environnement/`.env` via
  `alirpunkto/secret_manager.py` (clé de session dérivée de `SECRET_KEY`) ;
  aucun secret en dur dans le code. Le `.env` est chargé **une seule
  fois** au démarrage ; toutes les lectures passent ensuite par
  `os.getenv` — l'environnement réel du processus prime, plus aucun
  `get_key()` ne relit le fichier en exécution.
- **Amorçage LDAP** : le LDIF généré (identités et hashes) naît sous
  `umask 077` et finit en mode `0600` ; le générateur sait lire les
  mots de passe de variables d'environnement dédiées
  (`GENERATE_LDIF_*_PW`, purgées après lecture).
- **Écritures de groupes contrôlées** : chaque `conn.modify()` de
  `dynamic_groups` passe par `_checked_modify` — exception
  interceptée, retour vérifié, `conn.result` journalisé avec membre,
  groupe, opération et côté.
- **Transactions** : plus de `transaction.commit()` explicites dans les
  vues ; `pyramid_tm` garantit l'atomicité (audit 2026).
- **Robustesse LDAP** : tolérance aux schémas en retard
  (`schema_safe_attributes`) — un annuaire non à niveau ne provoque plus de
  déni de connexion.

## Protections d'infrastructure

Décrites et vérifiées dans `docker/README.md` et les audits Docker/Postfix :
anti-relais Postfix, port 25 non publié, DKIM/SPF/DMARC, segmentation
réseau du `compose`, sauvegardes, TLS.

## Limites connues et travaux cibles

- Les grands chantiers des quatre premiers passages sont **fermés** :
  la pile Docker démarre et se prouve par un smoke test de bout en
  bout (P0) ; les trois verrous hachés, l'image multiétape en wheel
  applicative et les bases épinglées par digest tiennent la chaîne
  d'approvisionnement (P1, finition 0075) ; TLS LDAP validant, cache
  serveur indexé, jeton de rafraîchissement scellé, réponses Keycloak
  validées, transport LDIF intégralement hors `argv` (enregistrements
  NUL sur l'entrée standard, champs requis obligatoires) et relation
  de groupes réconciliée — côté membre autoritatif, paires d'écritures
  fail-closed (P2, trains 0073→0076). Détail dans les versements des
  quatrième → onzième passages
  (`docs/fr/audits/2026080*_audit_externe_chatgpt_*`).
- Le dixième passage a montré la face sombre d'une migration
  d'interface : **trois casses P0 de notre fait** — double clé `args:`
  du compose (cachée par le chargeur permissif de PyYAML), `smoke.yml`
  et `init_test.sh` restés sur l'ancien contrat LDIF, le hachage shell
  de ce dernier poussant même chaque mot de passe dans l'argv d'un
  python. Réparées par le train 0078 : **émetteur commun**
  `docker/ldif_records.sh` sourcé par les trois appelants, tests
  transversaux des appelants, parseur YAML strict maison et porte
  `compose config --quiet` avant tout build. Onzième passage : 8,8/10.
- La **persistance d'une nouvelle sanction** n'est pas garantie si
  l'écriture autoritative (côté membre) échoue après le côté groupe :
  le passage suivant la traite en résidu et la retire au lieu de la
  rejouer (11ᵉ passage, §11) — une sanction est une *restriction*,
  l'asymétrie « perdre un octroi est sûr » ne lui convient pas.
  Décision de design en cours : attribut LDAP dédié, file de reprise,
  ou octroi membre-d'abord pour les groupes de restriction.
- La **sérialisation LDIF** interpole encore les valeurs en
  f-strings : un retour à la ligne dans un champ altérerait la
  structure du document — sérialiseur validant (refus de `\0`, `\r`,
  `\n`, base64 LDIF, validation UUID/rôles/langues/emails/dates),
  cible P2.
- **LDAPS n'est pas activé** dans la pile compose fournie
  (`LDAP_USE_SSL=false`, port 389 sur le réseau interne) : le
  mécanisme validant est prêt (`Tls` + `LDAP_CA_CERT_FILE`),
  l'activation et l'outillage certificats du conteneur LDAP sont une
  décision d'exploitation.
- Le **rappel des vérificateurs** vit encore dans l'événement
  `NewRequest` : exécution non garantie sans trafic, fragile en
  multi-processus — cible P3, sortie vers le cron (chapitre
  [09](09_taches_periodiques.md)).
- `.env.example` documente `MAIL_USE_TLS`/`MAIL_USE_SSL` là où le code
  lit `MAIL_TLS`/`MAIL_SSL`, présente `LDAP_SERVER` en URL et ignore
  `LDAP_CA_CERT_FILE` — cible P3.
- Le **scan quotidien des groupes** coûte membres × groupes en
  recherches LDAP — optimisation cible P3 (groupes chargés une fois,
  table inverse, recherche paginée).
- La **dette qualité** est un cliquet assumé : mypy observateur (124
  erreurs à l'adoption), Ruff limité à Pyflakes (`F841` en exception),
  plancher de couverture à 68 %, Certbot et CSP non testés.
- Les **ACL Pyramid** restent minimales ; la refonte par hiérarchie de
  classes est la cible (voir
  [06_autorisations_permissions](06_autorisations_permissions.md)).
- Le **chiffrement de bout en bout** imaginé à l'origine
  (`../specifications_historiques/Scénarios/Chiffrement de bout en bout.md`)
  est exploratoire et non implémenté.
