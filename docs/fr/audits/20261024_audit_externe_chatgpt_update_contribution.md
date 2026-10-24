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

## Second passage (même jour) — PHP 0.4 et train 0117 relus

L'auditeur valide la syntaxe du PHP 0.4 (PHP 8.4.24), l'architecture, le parcours CSRF et le nouveau contrat `success`/`partial`, et relève six points nouveaux.

| Réf. | Constat | Priorité | Disposition |
|---|---|---|---|
| P1 | Sous PHP 8, `curl_close()` est sans effet : le cookie jar est réécrit à la destruction du handle, après l'`unlink` | Élevée | **Corrigé** (PHP 0.4.1) : `unset($curl)` avant la suppression, nettoyage dans un `finally` englobant `initCurl`, fichier supprimé si `chmod` échoue |
| P2 | `assertStayedOnPortal` vérifiait après les redirections suivies ; un 307 externe aurait rejoué le POST d'identifiants | Élevée | **Corrigé** (PHP 0.4.1) : plus aucun suivi automatique ; le 302 du POST de connexion est reconnu sans être suivi, toute autre 3xx est une erreur ; comparaison schéma, hôte et port ; HTTP refusé hors `--allow-http` |
| P3 | Le client acceptait un `success` sans indicateurs, ou contredit par `groups_sync: error` | Élevée | **Corrigé** dans les deux clients : `financial_update`, `groups_sync`, `keycloak_sync` et une liste `groups` exigés |
| P4 | `ctype_digit` puis `(int)` saturait silencieusement à `PHP_INT_MAX` | Moyenne | **Corrigé** dans les deux clients : plafond métier d'un million de parts, débordement refusé |
| P5 | `sync_member_groups` rendait la cible même quand une écriture d'appartenance avait échoué : `groups_sync: success` à tort | Critique | **Corrigé** (train 0119) : chaque échec de `_checked_modify` est mémorisé, la fonction répond `None` ; tests sur grant refusé, révocation refusée et exception |
| P6 | `propagate_ldap_changes_to_keycloak` rendait `True` sans lire le compteur `failed` du `SynchronizationResult` | Critique | **Corrigé** (train 0119) : `sync_failed` lit `failed` et `status` ; un fournisseur en échec rend la propagation fausse, les autres sont tout de même synchronisés |

Limite rappelée par l'auditeur et maintenue : une propagation réussie prouve que le mécanisme a tourné, pas que chaque application a déjà rafraîchi ses droits.

## Troisième passage (même jour) — PHP 0.4.1 et train 0119 relus

L'auditeur confirme P1 à P6 corrigés (syntaxe PHP 8.4 vérifiée, P5 et P6 relus sur `master`) et relève six points nouveaux.

| Réf. | Constat | Priorité | Disposition |
|---|---|---|---|
| P7 | `getopt()` ignore silencieusement une option inconnue, mal orthographiée ou sans valeur : `--validitydate` laissait passer un paiement à moitié appliqué avec sortie 0 | P0 | **Corrigé** (PHP 0.4.2) : parseur `argv` strict maison — options inconnues, valeurs manquantes, doublons et arguments positionnels refusés |
| P8 | `--allow-http` acceptait n'importe quel hôte distant | Élevée | **Corrigé** (PHP 0.4.2) : réservé à `localhost`, `127.0.0.1` et `::1` |
| P9 | Plafond d'un million de parts présent dans les clients, absent du contrat serveur | Élevée | **Corrigé** (train 0120) : `MAX_SHARES` dans `update_contribution.py`, `400 invalid_value` au-delà ; un test vérifie l'égalité client/serveur. Le chiffre reste à valider par les règles de la coopérative |
| P10 | `trim` des valeurs `.env` non citées ; mot de passe visible dans la liste des processus via `--password` ; `--cookie` persistant sans contrôle de permissions | Moyenne | **Partiellement** (PHP 0.4.2) : l'aide documente les guillemets et recommande `.env` plutôt que `--password` ; un `--cookie` existant lisible par d'autres est refusé, un nouveau est créé en 0600. Le parseur `.env` reste minimal |
| P11 | `--help` exigeait les extensions `curl` et `dom` | Mineure | **Corrigé** (PHP 0.4.2) : analyse des arguments avant la vérification des extensions |
| P12 | `_group_side_groups` continuait sur une exception de lecture, groupe tenu pour vide : une appartenance à révoquer pouvait passer inaperçue et la convergence être annoncée | Élevée | **Corrigé** (train 0120) : la lecture illisible lève `GroupSideUnreadable`, `sync_member_groups` répond `None` sans rien écrire ; test sur une révocation avec côté groupe illisible |
| — | `sync_failed` tenait une réponse Keycloak de forme inconnue pour propre | Moyenne | **Corrigé** (train 0120) : seul un objet portant `failed` ou `status` est reconnu, tout le reste est un échec |
| — | Date `0000-01-01` acceptée par PHP, refusée par Python | Mineure | **Corrigé** dans les deux clients : année entre 1900 et 2199 |
| — | Formulation du code de sortie 0 : « confirmation des opérations de synchronisation », pas « droits restaurés partout » | Précision | **Reprise** dans l'en-tête des deux clients et dans la spécification |

## Journal

- 2026-10-24 : réception de l'audit, vérification de A2 dans `utils.py`, `dynamic_groups.py` et `views/update_contribution.py` (confirmé), exécution du train 0117 et de la version 0.4 du script PHP, versement de cette note.
- 2026-10-24 (second passage) : P5 et P6 confirmés à la lecture, train 0119 et PHP 0.4.1.
- 2026-10-24 (troisième passage) : P7 à P12, train 0120 et PHP 0.4.2.
