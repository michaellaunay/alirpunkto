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

- La **pile Docker documentée ne démarre pas** : contrôle `setup.py`
  disparu dans les deux scripts, option Waitress inconnue
  `use_forwarded_proto` (rejet vérifié en `ValueError`), écoute sur la
  boucle locale du conteneur — et `trusted_proxy = 127.0.0.1` qui,
  derrière le proxy compose, rabattrait le limiteur de connexions sur
  une seule adresse. Détail et plan dans l'audit du quatrième passage
  (`docs/fr/audits/20260801_audit_externe_chatgpt_alirpunkto_4e_passage.md`) ;
  correction P0 avec le smoke test Compose qui les aurait vus.
- `init.sh` transmet encore mots de passe et données personnelles par
  `argv` : le mécanisme `GENERATE_LDIF_*_PW` attend son branchement, et
  les données personnelles leur fichier temporaire `0600` (P2).
- Le **verrou unique** embarque les outils de test et de qualité dans
  l'image de production ; la séparation en trois verrous avec
  empreintes et l'image multiétape sont le P1.
- La synchronisation des groupes écrit les **deux côtés
  indépendamment** : un échec unilatéral peut laisser une divergence
  que le scan, qui lit `uniqueMemberOf` seul, ne voit pas (P2 : côté
  groupe autoritatif, scan comparant les deux côtés).
- Le **jeton de rafraîchissement** SSO réside dans le cookie de session
  signé mais non chiffré ; la cible est une session côté serveur — et,
  d'ici là, le chiffrement de la valeur (P2).
- Les **ACL Pyramid** restent minimales ; la refonte par hiérarchie de
  classes est la cible (voir
  [06_autorisations_permissions](06_autorisations_permissions.md)).
- Le **chiffrement de bout en bout** imaginé à l'origine
  (`../specifications_historiques/Scénarios/Chiffrement de bout en bout.md`)
  est exploratoire et non implémenté.
