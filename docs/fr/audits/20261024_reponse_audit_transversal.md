# Réponse à l'audit transversal du 24 octobre 2026 — trains 0122 à 0124

**Date** : 2026-10-24 · **Audit** : [audit transversal du projet](20261024_audit_complet_alirpunkto.md) (ChatGPT, commit figé `6f50670b`, train 0119) · **Réponse** : Claude (assistant de développement) · **Décision** : les trois P0 et les P1 circonscrits sont traités en trois trains ; quatre constats structurels restent ouverts et sont listés ci-dessous avec leur raison.

## Disposition par constat

| Réf. | Priorité | Constat (résumé) | Disposition | Train |
|---|---|---|---|---|
| A01 | P0 | Désactivation contournable par la récupération, `isActive` non lu, session réarmée par la page d'accueil | **Corrigé** : `is_account_closed` appliqué à la connexion LDAP, au retour SSO, à la demande de réinitialisation, au lien et à la session armée ; `isActive` chargé et typé ; l'accueil exige drapeau et charge utilisateur | 0122 |
| A02 | P0 | Relecture LDAP partielle : faits financiers et `isActive` non rafraîchis ; `get_member_by_oid(update=True)` rendait `None` | **Corrigé** : chaque attribut de l'annuaire est relu typé et appliqué ; absent ≠ vide (un fait absent vaut `None`, un attribut d'identité absent laisse le cache) ; le membre chargé est retourné ; test de divergence cache/annuaire à travers le vrai endpoint | 0122 |
| A03 | P0 | Champs internes affectables depuis le POST d'inscription | **Corrigé** : liste fermée `PUBLIC_REGISTRATION_FIELDS` ; parts, note, activité, rôle, IBAN, échéances viennent du modèle | 0122 |
| A04 | P1 | Retour SSO sans `state`, algorithme lu dans l'en-tête, émetteur non vérifié | **Corrigé** : `state` et vérificateur PKCE S256 à usage unique, horodatés ; liste d'algorithmes fixe ; émetteur vérifié | 0124 |
| A05 | P1 | Capacités de lien non spécialisées ni consommées | **Corrigé** : `link_matches_pending_action` (graine + usage) sur la réinitialisation, le changement d'adresse et la démission ; session de réinitialisation liée à la graine ; lien consommé après usage ; la démission frappe sa propre graine | 0124 |
| A06 | P1 | Purge : `TypeError` sur un vrai `Member`, résultat du `delete` ignoré, historique conservant les données | **Corrigé** : `Member.erase_personal_data`, contrôle du `delete` (`noSuchObject` reprend une passe interrompue), historique remis à zéro ; tests sur un vrai `Member` | 0123 |
| A07 | P1 | Branche mot de passe déclenchée par d'autres champs | **Corrigé** : `field == "password"`, une seule exécution ; test par la vraie vue | 0123 |
| A08 | P1 | Transitions locales avant les effets externes | **Corrigé pour les deux parcours cités** : démission et changement d'adresse écrivent l'annuaire d'abord, restent rejouables sur refus. **Non fait** : file d'effets persistante (« outbox ») générale | 0124 |
| A09 | P1 | Lectures de groupes échouées assimilées à un ensemble vide | **Corrigé par le train 0120** (`GroupSideUnreadable`, `read_member_groups`) ; la relecture de convergence des deux côtés après écriture reste à faire | 0120 |
| A10 | P1 | `ignored` accepté ; reprise quotidienne non garantie | **Corrigé** : `ignored` = non propagé ; marqueur persistant `var/keycloak_sync_pending` relancé par le scan quotidien même sans mouvement | 0123 |
| A11 | P1 | Singleton `Members` partagé entre connexions | **Non traité** : refonte de la résolution par `request.root` ; nécessite un test de concurrence à deux connexions et touche tous les appels sans connexion. À instruire séparément |  |
| A12 | P1 cond. | POST et corps de courriel en clair sous DEBUG | **Corrigé** : noms de champs seuls, métadonnées de courriel seules ; le diagnostic chiffré des secrets reste tel que décidé par le mainteneur | 0123 |
| A13 | P1 | Sauvegarde : mauvais chemin par défaut, succès sur archive incomplète | **Corrigé** : chemin de `production.ini`, échec si un magasin manque sauf `ALLOW_PARTIAL=1`, manifeste SHA-256, vérification de l'archive avant élagage, `umask 077`. **Non fait** : `repozo`, chiffrement, test de restauration (exploitation) | 0123 |
| A14 | P1 | Notifications financières désordonnées | **Non traité** : demande un identifiant d'opération et une séquence côté site commercial ; limite documentée dans `situation_financiere.md` |  |
| A15 | P1 | Client Python : priorité d'URL, HTTP, redirections, cookies | **Corrigé** : `--base_url` sans défaut (CLI > `.env` > défaut), HTTPS obligatoire sauf `--allow-http` local, `allow_redirects=False`, origine du 302 contrôlée, cookies en 0600 | 0123 |
| A16 | P2 | Gestion des prestataires sans contrôle du type de la cible | **Corrigé** : la cible doit être `PROVIDER` | 0123 |
| A17 | P2 | Budgets LDAP, pagination | **Non traité** : charge réelle non mesurée ; à instruire avec des métriques |  |
| A18 | P2 | Tests de frontières insuffisants | **Partiellement** : les trois trains ajoutent des tests sur vrais `Member`, vraie vue de profil, vrai chargeur sur annuaire simulé, vrai endpoint, vraie pile Pyramid (0117) ; la tranche LDAP de test et le parcours Keycloak isolé restent à construire | 0122-0124 |

## Preuves

- 0122 : 21 tests rouges sur l'arbre précédent, verts après ; suite 1235, couverture 75,37 %.
- 0123 : 16 tests rouges puis verts ; suite 1250, couverture 75,44 %.
- 0124 : 20 tests rouges puis verts ; suite 1269, couverture 76,39 %.
- ruff, bandit `-ll` verts à chaque train ; aucune dépendance modifiée.

## Ce qui reste ouvert

A11 (singleton), A14 (séquence des paiements), A17 (budgets LDAP), la file d'effets de A08, la relecture de convergence de A09, et les éléments d'exploitation de A13. Chacun demande soit une décision du mainteneur, soit un partenaire externe, soit une mesure sur l'instance réelle.
