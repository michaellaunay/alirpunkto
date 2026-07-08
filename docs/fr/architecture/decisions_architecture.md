# Décisions d'architecture

> Statut : registre courant. Format : contexte, décision, conséquences.
> Une décision « transitoire » est assumée mais destinée à évoluer ;
> « proposée » n'est pas encore mise en œuvre.

## ADR-001 — Pyramid (adopté)

Framework web léger, mûr, au routage explicite et à l'écosystème
transactionnel intégré (`pyramid_tm`, `pyramid_retry`, `pyramid_zodbconn`,
`pyramid_mailer`). Conséquence : la configuration est concentrée dans
`alirpunkto/__init__.py`.

## ADR-002 — ZODB (adopté)

Les objets métier (`Member`, `Candidature`) sont des graphes Python
persistés tels quels, avec transactions natives et sans ORM. Conséquences :
`FileStorage` mono-écrivain ; les outils hors-ligne ne doivent pas écrire
pendant que l'application tourne ; la ZODB est reconstructible depuis LDAP.

## ADR-003 — OpenLDAP comme référentiel d'identités (adopté)

Comptes, mots de passe et groupes vivent dans l'annuaire, interopérable
avec Keycloak et les applications tierces. Conséquence : double référentiel
(LDAP fait foi pour l'identité, la ZODB pour l'applicatif), synchronisé par
`update_member_from_ldap`.

## ADR-004 — Schéma LDAP spécifique (adopté)

`alirpunktoPerson` porte les attributs métier typés plutôt qu'un champ
fourre-tout. Conséquence : le schéma a des versions ; l'outillage de mise à
niveau idempotente (`tools/ldap_provision.py --update-schema`) et la
tolérance de lecture (`schema_safe_attributes`) en découlent.

## ADR-005 — Chameleon / TAL / METAL (adopté)

Continuité avec l'expérience Zope/Plone de l'équipe ; `layout.pt` factorise
la structure via METAL. Conséquence : gabarits proches du HTML, courbe
d'entrée douce pour les contributeurs venant de Plone.

## ADR-006 — Postfix local (adopté)

Relais maîtrisé (DKIM/SPF/DMARC, anti-relais) plutôt qu'un service tiers.
Conséquence : la délivrabilité est de la responsabilité de la pile ; le
durcissement est audité et documenté dans `docker/README.md`.

## ADR-007 — Docker (adopté)

Reproductibilité du déploiement et pile locale de test hors-ligne.
Conséquence : deux composes (production, test), scripts d'initialisation,
volumes nommés persistants.

## ADR-008 — Stratégie de tests (adopté)

LDAP simulé par défaut, pile Docker pour l'intégration, et surtout :
**chaque constat d'audit ou incident de terrain est clos par des tests
dédiés et datés**. Conséquence : la suite est aussi le journal des
régressions interdites.

## ADR-009 — Modèle de permissions actuel (transitoire)

Contrôles d'accès dans les vues + matrice fine par attribut
(`model_permissions.py`) ; ACL Pyramid réduite à `group:admins`. Assumé le
temps de la refonte (ADR-010).

## ADR-010 — Refonte des ACL par hiérarchie de classes (proposé)

Cible : faire dériver les `__acl__` et les `permission=` des vues de la
même source que la matrice par attribut, via une hiérarchie de classes de
ressources. Statut : décidé dans son principe, non implémenté.

## ADR-011 — Jetons SSO en session : rafraîchissement seul (adopté, 2026-07-08)

Le cookie de session (4093 octets) ne stocke que le jeton de
rafraîchissement et son échéance (`utils.store_sso_tokens`) ; l'*access
token*, jamais relu et gonflé par les revendications de groupes, en est
exclu. Cible complémentaire (proposée) : session côté serveur, qui lèverait
la contrainte de taille et sortirait le jeton du poste client.
