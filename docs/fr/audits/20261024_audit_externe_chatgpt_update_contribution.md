# Audit externe ChatGPT du 24 octobre 2026 — client d'encaissement et `/update_contribution`

**Date** : 2026-10-24 · **Auditeur** : ChatGPT (contre-expertise demandée par Michaël) · **Objet** : le script PHP du logiciel de paiement (`modify_contributor_alirpunkto.php`, version 0.3 portée la veille sur `/update_contribution`), comparé au code de `master` (`34a224f7`) et à `tools/update_cooperator.py` · **Verdict de l'auditeur** : fonctionnellement cohérent, pas assez robuste pour un usage financier sans surveillance · **Réponse** : train 0117 (dépôt) et version 0.4 du script PHP (hors dépôt).

## Constats et disposition

| Réf. | Constat | Priorité | Disposition |
|---|---|---|---|
| A1 | Sortie 0 quand aucune modification n'est demandée | Critique | **Corrigé** (PHP 0.4 et outil Python) : refus avant toute connexion, code 1 |
| A2 | `update_ldap_member` ignore les retours de `sync_member_groups` (None en échec) et de `notify_keycloak_of_directory_change` (False) ; `get_member_groups` rend `set()` sur erreur de lecture — une réponse `success` ne garantit pas les droits | Critique | **Corrigé** côté serveur : `propagate_member_change` rapporte `groups_sync` et `keycloak_sync` ; la réponse porte `financial_update`, ces deux statuts, `status: partial` quand l'un traîne, `groups: null` quand l'annuaire ne se relit pas ; un appel rejoué à faits inchangés relance la propagation pour réparer. Les deux clients traitent `partial` comme un échec à rejouer |
| A3 | Le client ne vérifie ni l'OID ni les valeurs retournées | Élevée | **Corrigé** (PHP 0.4 et outil Python) : OID et chaque fait envoyé comparés à la réponse |
| A4 | Pas de délai d'expiration HTTP ; redirections non bornées | Élevée | **Corrigé** : délais de connexion et de lecture dans les deux clients ; en PHP, redirections limitées, protocoles restreints, hôte de destination contrôlé |
| A5 | Fichier de cookies temporaire conservé après usage | Élevée | **Corrigé** (PHP 0.4) : fichier en 0600, supprimé dans le `finally` sauf `--cookie` explicite |
| A6 | Jetons CSRF écrits en mode verbeux | Moyenne | **Corrigé** (PHP 0.4) : plus aucun jeton ni corps complet dans les journaux |
| A7 | Statut HTTP de la connexion non inspecté : un 400 CSRF devenait « identifiants invalides » | Moyenne | **Corrigé** dans les deux clients : un 4xx sur le POST de connexion est nommé pour ce qu'il est |
| A8 | `.env` obligatoire même avec identifiants en ligne de commande ; `trim` des mots de passe ; parseur `.env` maison | Moyenne | **Partiellement** : `.env` optionnel quand les identifiants sont fournis ; le mot de passe n'est plus rogné ; le parseur ne retire que des guillemets de délimitation appariés. Un parseur dotenv tiers côté PHP reste à la main de la boutique |
| §3 | `tools/update_cooperator.py` se connectait sans jeton ni `Origin` (400 sur le fil) ; ses tests tournaient sur un `MagicMock` | Confirmé | **Corrigé** : séquence GET /login → POST avec jeton et `Origin` → GET /modify_member ; `tests/test_update_contribution_wire.py` fait passer `login` et `modify_member` par la vraie pile Pyramid (HTTPS, cookie sécurisé, garde CSRF) |
| §4 | Valeur absolue de parts : deux notifications désordonnées laissent l'ancien total | Moyen terme | **Non traité** ; limite documentée dans `situation_financiere.md`, à instruire avec la boutique (identifiant d'opération, séquence croissante) |
| §5 | `Throwable` plutôt qu'`Exception`, nom réel du programme, validation de `--base_url` (origine sans chemin), extensions `curl` et `dom` | Mineure | **Corrigé** (PHP 0.4) : `Throwable`, `$argv[0]`, contrôle d'origine, vérification des extensions au démarrage |

## Preuves du train 0117

- Nouveaux tests et tests remaniés sur l'état précédent du code (serveur et outil d'origine, tests neufs) : 30 rouges et 6 erreurs sur 39 ; après : 39 verts.
- Le rouge le plus parlant : `test_the_script_login_posts_the_login_page_token_with_the_origin` et, sur le fil, `test_a_bare_login_post_is_refused_by_the_csrf_guard` (400 « Bad CSRF token ») ; sans en-tête `Origin` en HTTPS, 400 « Bad CSRF Origin », vérifié par sonde WebTest le 24 octobre.
- Suite complète, ruff, bandit : voir le message de commit du train.

## Journal

- 2026-10-24 : réception de l'audit, vérification de A2 dans `utils.py`, `dynamic_groups.py` et `views/update_contribution.py` (confirmé), exécution du train 0117 et de la version 0.4 du script PHP, versement de cette note.
