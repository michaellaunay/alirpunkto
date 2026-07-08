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
  aucun secret en dur dans le code.
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

- Le **jeton de rafraîchissement** SSO réside dans le cookie de session
  signé mais non chiffré ; la cible est une session côté serveur.
- Les **ACL Pyramid** restent minimales ; la refonte par hiérarchie de
  classes est la cible (voir
  [06_autorisations_permissions](06_autorisations_permissions.md)).
- Le **chiffrement de bout en bout** imaginé à l'origine
  (`../specifications_historiques/Scénarios/Chiffrement de bout en bout.md`)
  est exploratoire et non implémenté.
