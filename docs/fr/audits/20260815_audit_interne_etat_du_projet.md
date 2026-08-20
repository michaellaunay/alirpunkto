# Audit interne complet — état du projet AlirPunkto

**Date** : 2026-08-15 · **Auditeur** : Claude (assistant de développement, auteur des trains 0063-0110) · **Référence** : master `29809281` + trains 0109/0110 · **Douzième passage** de la série d'audits (le onzième, externe, avait noté 8,8/10).

## 1. Volumétrie et vitalité

Le cœur applicatif pèse **11 228 lignes de Python** (hors locales) pour **13 123 lignes de tests** répartis en **104 fichiers** — le ratio tests/code dépasse 1,17, rare et sain. **33 catalogues** de traduction plus le POT, tous synchronisés et compilés. La suite compte **1 082 tests verts** en ~2 minutes, couverture **72 %** (plancher CI à 68 %). Quatre workflows CI (tests, qualité, smoke, test-stack) sont au vert, le dernier produisant à chaque passage le **manuel utilisateur régénéré** avec captures — la documentation vivante promise est tenue.

## 2. Acquis majeurs du cycle (juillet-août 2026)

**i18n structurellement saine** (trains 0098-0100) : registre unique `SUPPORTED_LOCALES` (33 langues), couverture POT complète verrouillée, politique de repli anglais explicite et non-fuzzy, verrou « tout msgid utilisé est au POT » — la classe de bogue « clé brute à l'écran » (#252) ne peut plus réapparaître silencieusement. **Campagne client soldée** (trains 0101-0109) : seize tickets fermés en une semaine, dont trois causes profondes — les flash jamais rendus nulle part (#251), le repli de locale qui n'attrapait rien car `AssetResolver.resolve` ne lève jamais (#254), et l'enum TYPE assigné au champ ROLE depuis l'origine (#264, que mypy signalait). **L'annuaire des membres** (#249) : ouvert à tous avec fiches cadrées par rôle, libellés neutres dans 34 catalogues. **Une faille réelle fermée** (#265) : un compte désactivé pouvait se reconnecter — la garde des états de départ est posée et verrouillée dans les deux sens. **L'infrastructure** : l'incident certificat de kuneagi02 a été soigné en profondeur (renouvellement par plugin apache, in-place, sans hooks tueurs de PID 1) ; la prod se renouvelle seule.

## 3. Sécurité — état

Acquis vérifiés : hachage des mots de passe conforme (famille de tests dédiée), throttle de connexion, CSRF systématique, garde anti-open-redirect (23 tests), protection des jetons SSO, en-têtes durcis côté Apache, `bandit -ll` muet, chaîne d'approvisionnement épinglée (actions par SHA, locks hachés), secrets hors dépôt avec référence versionnée sans secret. Points d'attention restants, par ordre de gravité décroissante : **(a)** le flux upgrade→vote n'a jamais été joué de bout en bout par un navigateur réel — le fix #256 est verrouillé structurellement mais le scénario Playwright reste le juge attendu ; **(b)** la désactivation ne verrouille pas le compte côté LDAP (la garde applicative suffit tant que tout passe par AlirPunkto, mais un accès annuaire direct authentifierait encore) ; **(c)** pas de 2FA — acceptable au stade, à inscrire à la feuille de route ; **(d)** TLS delfeno en snakeoil (mail, hors périmètre applicatif).

## 4. Dette technique, mesurée

**mypy : 130 erreurs** (job « informative », jamais bloquant ; 124 au train 0070, 132 au pic, 130 aujourd'hui — le #264 en a soldé) : un cliquet « le compte ne peut que décroître » est proposé et coûterait vingt lignes. **Chaînes orphelines au POT** : le nettoyage P2 de l'audit i18n reste à faire (`error_committing_candidature` et consorts). **Le rôle n'existe pas au LDAP** : dérivé du type à la lecture (correct fonctionnellement), un attribut dédié serait plus propre si les rôles divergent un jour des types. **Deux gestes delfeno** documentés non appliqués (virtual_domains, RBL nu). Aucune dette n'est cachée : chaque point vit dans une issue, le carnet, ou ce document.

## 5. Gouvernance du code

Les conventions tiennent sous charge : Conventional Commits développés, patchs numérotés vérifiés sur clone vierge avant livraison, séquences prouvées quand les trains s'empilent, démos rouge/verte, leçons codifiées en verrous (le test « un helper entre @view_config et la vue » a attrapé son auteur cette semaine — c'est exactement son travail). Le harnais multi-agents (`AGENTS.md`, chapitre 14) est en place pour la suite annoncée.

## 6. Note et recommandations

**Note : 9,1/10** (+0,3 sur le onzième passage). Le projet gagne sur la sécurité effective (#265), la santé i18n verrouillée, et la boucle client d'une réactivité rare ; il perd ses derniers dixièmes sur le scénario e2e upgrade→vote manquant, le verrouillage LDAP des départs, et la dette mypy non cliquetée. Recommandations priorisées : **P1** le scénario Playwright upgrade→vote (juge du #256, matière à manuel) ; **P2** le verrouillage LDAP à la confirmation de désactivation (complément du #265) ; **P3** le cliquet mypy ≤130 ; **P4** le nettoyage des orphelins POT ; **P5** l'attribut rôle au schéma LDAP.

*Ce document est versé dans `docs/fr/audits/` conformément à la tradition de la série ; il constitue l'état de référence avant la bascule vers le développement multi-agents.*
