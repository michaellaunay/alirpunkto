# Audit transversal du projet AlirPunkto

**Date :** 24 octobre 2026  
**Référentiel :** `michaellaunay/alirpunkto`, branche `master`  
**Commit figé :** `6f50670bad6a2b5ff20024b53d02be48b5d7a03d` — train 0119  
**Nature :** revue du code et de l’architecture, vérification des résultats CI, contre-tests isolés et plan de correction. Aucun changement du dépôt ni de la production.

## Synthèse de décision

Le projet dispose d’une chaîne de qualité réelle : dépendances verrouillées avec empreintes, analyse statique et recherche de secrets, tests Python, démarrage Docker et scénarios navigateur. Les corrections récentes du CSRF et des confirmations financières apportent un progrès tangible. Elles ne suffisent cependant pas à établir une garantie de sécurité et de cohérence de bout en bout.

**Je déconseille d’étendre l’exploitation automatisée avant de fermer les trois priorités P0 : autorisation des comptes désactivés, vérité des données financières relues depuis LDAP, et affectation de champs internes pendant l’inscription.** Le parcours SSO, la purge et la reprise des opérations partielles requièrent ensuite un traitement prioritaire.

Le problème central n’est pas le nombre de tests. Plusieurs frontières métier restent insuffisamment définies : un état de récupération peut remplacer un état de départ ; une lecture LDAP ne rafraîchit qu’une partie de l’objet ; un changement de profil peut entrer dans la branche « mot de passe » ; une opération externe peut réussir alors que la transaction locale échoue. Les tests existants ne modélisent pas toujours ces interactions.

## 1. Méthode, portée et limites

Le commit a été identifié par l’API GitHub puis utilisé explicitement pour les lectures. La revue couvre les principaux modules d’authentification, les vues d’inscription et de gestion des membres, les modèles, les accès LDAP, les groupes dynamiques, la propagation Keycloak, les tâches périodiques, les clients financiers, la configuration de production, la sauvegarde et les workflows de CI. Certaines grandes sources ont été lues par plages ciblées ; ce rapport ne prétend pas avoir inspecté chaque traduction ou chaque ressource statique du dépôt.

Le connecteur GitHub a permis de lire les sources et les journaux. Le clone depuis le conteneur de calcul n’a pas abouti, notamment en raison de la résolution réseau. Les dépendances Pyramid, LDAP3 et ZODB n’y sont pas installées. **La suite complète n’a donc pas été relancée localement**, ni la pile Docker, ni une instance Keycloak réelle. La production n’a été ni sondée ni modifiée.

Douze contre-tests ont été exécutés localement : onze sondes Python sur des corps de fonctions recopiés depuis le commit, avec dépendances externes simulées, et une sonde du parseur du PHP fourni. Les premières ne sont pas des tests d’intégration de l’application. Le fichier `contre_tests_audit.py` permet aussi d’extraire les fonctions par AST depuis un vrai clone, sans importer l’application et sans lire ses secrets. Les résultats et les extraits sont joints afin de rendre cette distinction vérifiable.

Les niveaux de priorité sont des décisions de traitement, pas des scores CVSS : **P0** bloque une nouvelle mise en production automatisée ; **P1** appelle une correction prioritaire ; **P2** relève du durcissement ou d’une clarification de contrat. Un constat structurel n’est pas présenté comme une exploitation observée en production.

### Résultats CI effectivement consultés

La révision dispose de quatre workflows terminés avec succès : `quality`, `Tests`, `smoke` et `test-stack`. Le workflow `Tests` n° 40101285729 a réussi sur Python 3.11 et 3.12. Le journal du job Python 3.12 n° 120893780557 indique **1 205 tests réussis, 7 avertissements, couverture de 74,82 %**, seuil bloquant de 68 %. Le message du commit annonce 74,71 % : il s’agit d’une autre mesure, qu’il ne faut pas substituer à celle du job consulté.

| Module | Couverture affichée dans ce job |
|---|---:|
| `views/sso_login.py` | 24 % |
| `views/register.py` | 52 % |
| `utils.py` | 64 % |
| `views/modify_member.py` | 71 % |
| `views/forgot_password.py` | 77 % |
| `views/update_contribution.py` | 92 % |
| `models/member.py` | 96 % |
| `keycloak_sync.py` | 98 % |

Ces chiffres mesurent des instructions exécutées, pas la validité de toutes les garanties métier. La très forte couverture d’un module ne remplace pas un test de son interaction avec les objets réels et les services externes.

## 2. Architecture et invariants à stabiliser

Le navigateur ou le client financier passe par Apache/Waitress et Pyramid. Les membres et candidatures possèdent un état dans ZODB ; les identités, attributs financiers et appartenances sont également conservés dans LDAP. Les groupes alimentent Keycloak, puis les applications consommatrices. Les courriels et la maintenance ajoutent d’autres effets externes.

Il faut rendre explicites les invariants suivants : LDAP est l’autorité des attributs qui lui appartiennent ; une donnée inconnue n’est jamais équivalente à une donnée vide ; une récupération de mot de passe ne réactive pas une identité ; un succès financier correspond aux valeurs effectivement enregistrées ; une confirmation de propagation ne se déduit pas de l’absence d’exception ; et une purge ne conserve pas clandestinement les données dans l’historique.

L’approche recommandée reste compatible avec Pyramid, LDAP et ZODB. Elle ne nécessite pas une réécriture du projet : un adaptateur LDAP central, une politique d’autorisation commune, des transitions d’état distinctes, des capacités à usage unique et une file persistante d’effets externes suffisent à traiter l’essentiel.

## 3. Registre des constats

| Réf. | Priorité | Constat | Validation |
|---|---|---|---|
| A01 | P0 | Désactivation fragilisée par la récupération et le chargement LDAP | Source, scénario transversal à intégrer |
| A02 | P0 | Cache incomplet : fausse confirmation possible des faits financiers | Source ; sondes sur `get_member_by_oid` |
| A03 | P0 | Affectation de champs internes à partir de l’inscription | Source, validation LDAP ultérieure identifiée |
| A04 | P1 | Retour SSO non lié à une transaction du navigateur | Source et référentiel OAuth |
| A05 | P1 | Capacités de récupération/confirmation insuffisamment consommées et spécialisées | Source |
| A06 | P1 | Purge incompatible avec `Member.email` et conservation de données dans l’historique | Source et sondes isolées |
| A07 | P1 | Branche mot de passe appliquée à d’autres champs du profil | Source |
| A08 | P1 | Transitions locales confirmées avant la réussite des effets externes | Source et modèle transactionnel |
| A09 | P1 | Lectures LDAP échouées assimilées à une absence de groupes | Source et sondes isolées |
| A10 | P1 | Synchronisation Keycloak ignorée acceptée ; reprise quotidienne non garantie | Source et sondes isolées |
| A11 | P1 | Singleton `Members` partagé entre connexions/requêtes | Risque structurel, concurrence à reproduire |
| A12 | P1 conditionnelle | Mot de passe et liens sensibles journalisés en clair avec DEBUG | Source ; niveau WARN en production par défaut |
| A13 | P1 | Sauvegarde : mauvais chemin par défaut et succès possible sur contenu incomplet | Source/configuration |
| A14 | P1 | Notifications financières désordonnées et reprises devenues obsolètes | Source et scénario déterministe |
| A15 | P1 | Client Python : priorité d’URL erronée, HTTP et redirections sensibles | Source ; sonde CLI du PHP en annexe |
| A16 | P2 | Gestion des prestataires sans validation du type de la cible | Source ; impact limité au rôle administrateur |
| A17 | P2 | Budgets LDAP, pagination et coût des parcours à expliciter | Source, charge réelle non mesurée |
| A18 | P2 | Tests de frontières et d’objets réels insuffisants malgré une CI verte | Sources CI/tests et contre-tests |

## 4. Détail des anomalies et corrections

### A01 — La désactivation n’est pas un invariant d’autorisation

**Sources :** `views/forgot_password.py`, `views/login.py`, `views/sso_login.py`, `views/home.py`, `utils.py::update_member_from_ldap`, `models/member.py::MemberDatas`.

La demande de réinitialisation affecte `DATA_MODIFICATION_REQUESTED` au membre sans exclure d’abord les états `UNSUBSCRIBED`, `EXCLUDED` ou `DELETED`. Le login LDAP refuse certains états de départ, mais ne teste pas directement `is_active`. Le chargement depuis LDAP demande `isActive` sans le recopier dans les données du membre ; un objet nouvellement construit reçoit le défaut `is_active=True`. Le parcours SSO dépend pourtant de ce champ pour refuser un compte désactivé.

**Scénario :** un ancien titulaire, qui connaît encore son mot de passe, demande une réinitialisation. L’état local de départ peut être remplacé. Si LDAP accepte encore son bind — une propriété métier `isActive=False` n’est pas à elle seule un verrou natif de bind dans le code fourni — le garde du login peut ne plus bloquer la connexion. Il ne s’agit pas d’une connexion sans mot de passe ; il s’agit d’un contournement possible de la révocation. La présence éventuelle d’une politique LDAP extérieure n’a pas été vérifiée.

Les sessions existantes constituent une deuxième frontière : plusieurs vues vérifient seulement les clés de session. `home_view` remet `logged_in=True` lorsqu’une clé `user` existe. Il faut vérifier l’identité autorisée, et non faire de ces deux champs redondants une politique d’accès.

**Correction :** séparer le statut durable du compte des workflows temporaires ; charger un état d’activité LDAP typé ; centraliser l’autorisation des requêtes sensibles ; introduire une version de session ou un mécanisme de révocation contrôlé côté serveur. La récupération ne doit jamais modifier le statut durable.

**Critère de réception :** les comptes inactifs, exclus ou démissionnaires restent refusés après demande de reset, après ouverture du lien, après redémarrage/reconstruction ZODB, par login LDAP, par SSO et avec un ancien cookie.

### A02 — La « relecture LDAP » ne recharge pas les faits financiers

**Sources :** `utils.py::get_member_by_oid`, `utils.py::update_member_from_ldap` (environ 729–900), `views/update_contribution.py` (126–204).

Le chargement LDAP lit les parts, la validité, la note, les groupes, l’IBAN et d’autres attributs. Pour un membre déjà présent, il ne met pourtant à jour qu’un sous-ensemble : adresse, pseudonyme, type, noms, nationalité, naissance, langues 1 et 2. Les faits financiers et `isActive` n’y sont pas réaffectés. Les valeurs vides ne remplacent pas toujours les anciennes valeurs à cause des conditions de vérité.

L’endpoint compare ensuite la demande à cet objet. **Exemple : cache ZODB à 3 parts, LDAP à 1, demande de 3.** La comparaison peut conclure « unchanged », ne pas écrire les parts, puis répondre 3 à partir du cache. Les groupes sont calculés depuis LDAP : leur synchronisation peut réussir tout en laissant faux le fait financier confirmé au client.

Autre défaut précis : sur un cache manquant, `get_member_by_oid(update=True)` appelle le chargement mais affecte ensuite `member=None` et retourne `None`. Deux sondes reproduisent ce résultat et l’absence de rafraîchissement d’un objet déjà en cache. La documentation du paramètre indique un chargement si absent : il faut donc distinguer ce contrat d’un véritable « force refresh » et ne pas confondre les deux dans les contrôles d’autorisation.

**Correction :** un convertisseur LDAP → objet complet et typé, appliqué à la création et au rafraîchissement ; distinction absent/vide/inconnu ; retour du membre effectivement chargé ; confirmation financière depuis l’état autoritatif et non depuis un cache susceptible d’être périmé.

**Tests :** cache divergent dans les deux sens ; LDAP `0`, `False` et champ effacé ; cache vide ; état LDAP modifié hors application ; relecture après écriture. Vérifier à la fois LDAP, ZODB et la réponse JSON.

### A03 — L’inscription peut affecter des champs réservés au système

**Sources :** `views/register.py::handle_confirmed_human_state`, `utils.py::register_user_to_ldap`.

La validation `form.validate(items)` est commentée. Une partie des contrôles est faite manuellement, puis les champs de `MemberDatas` sont repris depuis `request.params`. Ce n’est pas une liste des champs autorisés à l’inscription ; c’est le modèle interne qui sert de liste d’entrée.

Le nombre de parts et la note de comportement font partie de ces données. Le chemin d’enregistrement d’un coopérateur les transmet ensuite à LDAP. L’existence d’une étape de validation d’identité ne valide pas pour autant ces montants et cette note.

**Portée exacte :** je ne conclus pas à la création immédiate d’un administrateur ni à l’obtention automatique de tous les droits. Les types de membre et d’autres conditions ont leurs propres contrôles. L’anomalie démontrée est la possibilité de faire cheminer des données financières/de comportement choisies par le demandeur jusqu’à l’enregistrement.

**Correction :** utiliser un schéma d’entrée distinct, une liste fermée de champs publics et des valeurs internes imposées côté serveur. Refuser ou ignorer explicitement tout champ réservé ; les parts initiales et les données financières ne doivent pas venir du formulaire public. Valider la requête entière avant toute mutation ou effet externe.

**Tests :** inscription ordinaire et coopérateur avec paramètres supplémentaires `number_shares_owned`, `cooperative_behaviour_mark`, rôle et activité. Vérifier l’absence d’influence sur les données internes et LDAP, y compris après approbation normale.

### A04 — Le callback SSO manque de liaison avec la demande initiale

**Source :** `views/sso_login.py`. **Référentiel externe :** RFC 9700, sections 2.1 et 4.7.

Le départ vers Keycloak n’enregistre pas de `state` aléatoire à usage unique lié à la session. Le callback accepte un `code` sans vérifier cette liaison ; aucune paire PKCE ni vérification de `nonce` équivalente n’est visible dans ce parcours. Le garde CSRF des formulaires ne remplace pas cette protection du retour OAuth.

La validation JWT mérite aussi un durcissement : algorithme lu depuis l’en-tête non vérifié, audiences larges, absence de validation explicite de l’émetteur dans l’appel examiné. Cela ne prouve pas que l’on puisse forger une signature : il faut fixer les paramètres attendus plutôt que les déduire du jeton.

**Correction :** `state` généré et consommé côté serveur, expiration courte, PKCE S256 et `nonce` lorsque l’ID Token est utilisé ; validation explicite de l’émetteur, du destinataire et de l’algorithme configuré. Ne pas supprimer le login LDAP pour corriger ce parcours.

**Tests :** callback sans départ préalable ; état manquant, faux, périmé ou réutilisé ; code d’une autre session ; émetteur et audience inattendus. Exécuter aussi un vrai parcours Keycloak isolé.

### A05 — Les liens d’action et la session de récupération ne sont pas suffisamment spécialisés

**Sources :** `views/forgot_password.py`, `views/check_new_email.py`, `views/unsubscribe.py`, `utils.py::decrypt_oid`.

Les liens Fernet possèdent bien une durée de validité : ce rapport ne signale pas une absence générale de TTL. Le défaut porte sur l’utilisation de la capacité après cette première vérification.

Dans la récupération de mot de passe, un lien accepté arme `session[MEMBER_OID]`. Le POST de modification peut ensuite se fonder sur cet identifiant, sans revalider la graine du lien initial ni consommer une autorisation dédiée à usage unique. Une copie du cookie armé ne doit pas pouvoir autoriser plusieurs changements successifs ou survivre à une nouvelle demande de reset.

Dans `check_new_email` et `unsubscribe_confirm`, le jeton est déchiffré en OID et graine, mais la graine n’est pas comparée à celle de l’opération en attente. La même primitive sert à plusieurs usages. Un jeton encore valide pour le même membre n’est donc pas suffisamment lié à une action précise et à une émission précise. La démission vérifie un état pending et son ancienneté, ce qui réduit l’exposition sans corriger la spécialisation du jeton.

**Correction :** capacité contenant/identifiant `subject`, `purpose`, `nonce`, expiration et état consommé, enregistrée côté serveur. Au POST, revalider et consommer atomiquement. Invalider les anciennes capacités lors d’un changement de mot de passe. Un GET de lien peut afficher une page de confirmation, mais l’action destructive devrait être confirmée explicitement.

**Tests :** ancien lien après réémission ; lien d’un autre usage ; ancienne session de reset après succès ; expiration entre ouverture et POST ; double clic et concurrence.

### A06 — La purge échoue avec un véritable membre et conserve des données historiques

**Sources :** `utils.py::purge_unsubscribed_members`, `models/member.py::email`, `::data`, `::_memorize_changes`, `maintenance.py`, `tests/test_unsubscribe.py`.

La purge supprime l’entrée LDAP puis affecte `member.email=None`. La propriété `Member.email` exige une chaîne : **`TypeError: The email must be a string.`** Le corps de cette propriété, exécuté dans une sonde isolée avec la fonction de purge, reproduit l’erreur après l’appel LDAP. La maintenance intercepte l’exception et annule sa transaction ZODB ; elle ne peut pas annuler la suppression externe déjà réalisée.

Le booléen renvoyé par `conn.delete` n’est pas contrôlé. Un refus sans exception ne bloque donc pas immédiatement le parcours. Une deuxième sonde le reproduit.

Enfin, `member.data = MemberDatas(...)` passe par une propriété qui mémorise l’ancienne donnée dans `_modifications`. Même après correction du `None`, le remplacement ne démontre donc pas un effacement des anciennes données personnelles. Une sonde montre que l’ancien objet reste référencé.

Le test existant utilise `SimpleNamespace` comme membre : il n’a pas la propriété restrictive et masque ce défaut. Il faut tester un véritable `Member` persisté.

**Correction :** modèle explicite de membre effacé, purge des historiques et des autres références selon la politique de rétention, contrôle du résultat LDAP, progression idempotente et récupérable. Isoler les erreurs par membre sans abandonner tout le lot ; ne confirmer la purge qu’après les vérifications prévues. Planifier également le traitement des anciennes révisions ZODB et sauvegardes ; aucune conclusion juridique globale n’est tirée ici.

### A07 — Le traitement du mot de passe intercepte les autres champs du profil

**Source :** `views/modify_member.py`, boucle des champs modifiables, environ 435–655.

La branche est conditionnée par `"password" in request.POST and "password" in writable_fields`, et non par `field == "password"`. Dans une boucle qui traite une langue, un nom ou une description, la simple présence d’un champ password peut donc faire entrer dans le traitement du mot de passe.

Avec un password optionnel vide, une modification d’un autre champ peut être refusée avec « password required ». Avec un password renseigné, cette branche peut s’exécuter à la place de la modification normale, éventuellement plusieurs fois. L’effet exact dans le navigateur dépend du formulaire envoyé ; l’erreur de dispatch dans le code est certaine.

**Correction :** traiter le changement de mot de passe une seule fois et séparément ; valider tous les champs avant mutation ; appliquer ensuite les données autorisées. Ne pas dépendre de l’ordre des champs du modèle.

**Tests :** changement de langue avec password absent puis vide ; changement simultané langue + password ; refus de confirmation différente ; un seul appel au changement de mot de passe.

### A08 — L’échec d’un effet externe peut laisser un état local définitif

**Sources :** `views/unsubscribe.py::unsubscribe_confirm`, `views/check_new_email.py`, `views/modify_member.py`, `production.ini`, initialisation de `pyramid_tm`/`pyramid_retry`.

La confirmation de démission met le membre à `UNSUBSCRIBED` avant d’appeler LDAP. En cas d’échec, la vue retourne un contexte d’erreur sans restaurer l’état ni annuler explicitement la transaction. L’appel suivant dispose d’un retour anticipé « déjà démissionné » qui ne retente pas l’écriture LDAP. Le changement d’adresse consomme pareillement `new_email` et remplace l’adresse avant la réussite de l’écriture externe.

Retourner un dictionnaire contenant `error` n’annule pas une transaction. Inversement, l’annulation ZODB ne revient pas sur une écriture LDAP déjà réalisée. Les trois tentatives configurées pour les conflits ne constituent pas un protocole de transaction distribuée.

**Correction :** état intermédiaire explicite, résultat des effets persisté, reprise idempotente et confirmation seulement après réussite. Une file d’opérations persistante (« outbox ») permet de reprendre les effets externes et de distinguer terminé/partiel/en échec. Un simple ajout d’`abort()` ne suffit pas à annuler ce qui a déjà été écrit dans LDAP.

**Tests :** refus LDAP, LDAP réussi puis conflit ZODB, arrêt du processus entre les deux, double requête. Vérifier qu’une nouvelle tentative répare la situation au lieu d’annoncer un succès fictif.

### A09 — Une lecture de groupes inconnue est transformée en ensemble vide

**Sources :** `dynamic_groups.py::_group_side_groups`, `::_read_current_groups`, `::read_member_groups`, `ldap_factory.py`.

Les erreurs d’écriture sont maintenant suivies, mais certaines lectures ne le sont pas. `_group_side_groups` journalise une exception puis continue ; les booléens/résultats de `search` ne sont pas systématiquement contrôlés. `_read_current_groups` retourne un ensemble vide quand aucune entrée n’est disponible, y compris après une recherche refusée sans exception.

Trois sondes reproduisent ces comportements. La documentation LDAP3 confirme que le résultat d’opération et la politique `raise_exceptions` doivent être pris en compte. Le fait d’avoir une connexion ouverte ne prouve pas la réussite d’une recherche.

**Conséquence :** une appartenance résiduelle à retirer peut ne pas être observée ; le synchroniseur peut construire un résultat à partir d’un état incomplet. Il ne faut pas récompenser une lecture inconnue par un succès.

**Correction :** adaptateur LDAP avec résultats typés succès/absence/erreur, propagation de l’échec de lecture et relecture de convergence des deux côtés lorsque le contrat l’exige. Traiter aussi les résultats partiels et les limites de recherche.

### A10 — « Synchronisation ignorée » et nouvelle tentative SSO

**Sources :** `keycloak_sync.py::sync_failed`, `dynamic_groups.py::daily_group_scan`, `utils.py::propagate_member_change`. **Référentiel externe :** `SynchronizationResult` de Keycloak expose explicitement `ignored`.

Le correctif du compteur `failed` est utile. Cependant, `sync_failed` considère comme propres les réponses non objets et ne traite pas `ignored`. Une sonde avec `ignored=True` et `failed=0` retourne `False`, donc « pas d’échec ». Cela ne démontre pas que les modifications ont été importées. Le cas doit être classé en attente/inconnu, pas automatiquement comme succès.

La maintenance n’appelle Keycloak que si les groupes changent durant le scan. Si LDAP a été corrigé hier mais que Keycloak était indisponible, aujourd’hui `before == after` et il n’y a pas nécessairement de nouvelle notification. La sonde de deux scans montre un seul appel à Keycloak, malgré l’échec simulé du premier.

**Correction :** validation stricte des formats et compteurs reconnus ; statut distinct pour une opération ignorée ; journal persistant de synchronisations restant à faire, indépendante du fait qu’un nouveau delta LDAP apparaisse ; backoff borné et alerte après plusieurs échecs.

**Test :** LDAP convergé + Keycloak indisponible, puis rétabli au scan suivant sans nouveau paiement : la propagation doit être relancée. Ne pas déduire de cette réussite que toutes les applications ont déjà renouvelé leurs jetons/caches.

### A11 — `Members._instance` n’est pas isolé par connexion

**Sources :** `models/member.py::Members.get_instance`, `__init__.py::root_factory`, `maintenance.py`.

La classe conserve une référence globale mutable à une collection liée à une connexion ZODB. Le passage d’une autre requête peut remplacer cette référence ; des appels sans connexion explicite peuvent alors utiliser la dernière collection attachée. La maintenance comporte déjà une précaution pour ne pas rebinder ce singleton, ce qui confirme que cette frontière est importante.

C’est un risque structurel de concurrence, pas une corruption que j’aurais observée sur la production. Il mérite un test à deux connexions avec des barrières de synchronisation, pas seulement des tests séquentiels.

**Correction :** résolution depuis `request.root` ou la connexion explicitement passée ; suppression de l’état global mutable pour les objets persistants ; conservation possible des constantes et caches réellement immuables. Ne pas confondre cette correction avec les constantes globales de configuration, qui sont un choix distinct du projet.

### A12 — Les journaux DEBUG peuvent contenir le mot de passe en clair

**Sources :** `views/register.py::_handle_candidature_state`, `utils.py::send_email`, `secret_manager.py`, `production.ini`.

L’inscription journalise `request.POST` en entier. Ce dictionnaire peut contenir `password` et `password_confirm`. La journalisation des courriels comprend aussi leur corps, donc potentiellement des liens d’action et des données personnelles. Ces traces contournent le mécanisme prévu de diagnostic chiffré des secrets.

**Condition importante :** la configuration de production examinée est au niveau WARN. Je ne prétends pas que le mot de passe figure actuellement dans les journaux du serveur. Le risque apparaît lorsque DEBUG est activé pour diagnostiquer un incident, ou dans une configuration différente.

**Correction :** journaliser une liste fermée de métadonnées, jamais un POST complet ni un corps de courriel ; masquer les liens d’action. Le mécanisme volontaire de diagnostic chiffré peut rester séparé, opt-in et encadré, sans clé privée sur le serveur.

**Test :** capturer les journaux DEBUG d’une inscription avec des marqueurs de test et vérifier l’absence du password, de sa confirmation et du token, y compris en exception.

### A13 — La sauvegarde livrée peut être erronée ou incomplète

**Sources :** `docker/backup.sh`, `production.ini`, `docker/start_pyramid.sh`.

Le script utilise par défaut `/home/alirpunkto/app/var/Data.fs`, tandis que la configuration utilise `var/filestorage/Data.fs`. Le script peut donc échouer sur une installation conforme aux valeurs livrées, sauf surcharge explicite de `ZODB_PATH`.

S’il ne trouve pas un conteneur actif, le script avertit puis continue. Il peut produire une archive partielle, voire vide, annoncer sa réussite et purger les anciennes archives. Aucune validation de complétude n’est imposée avant cette rétention. Les données LDIF et ZODB demandent aussi une protection explicite des permissions et du stockage hors hôte.

**Correction :** dériver le chemin de la configuration ou aligner les défauts ; échouer si un composant requis manque ; produire un manifeste avec fichiers, tailles, empreintes et révision applicative ; ne lancer la rétention qu’après validation ; `umask 077`, chiffrement selon l’environnement et test régulier de restauration. Utiliser un mécanisme cohérent de sauvegarde FileStorage, tel que `repozo`, plutôt que considérer le commentaire sur une copie à chaud comme une preuve de restauration.

**Réception :** restaurer LDAP et ZODB dans une pile vierge et vérifier une connexion, un profil, les attributs financiers et un parcours de reprise. Fixer RPO/RTO à partir du besoin réel ; ils n’ont pas été mesurés ici.

### A14 — La reprise d’un ancien paiement peut écraser un état plus récent

**Sources :** `views/update_contribution.py`, clients financiers, documentation de la situation financière.

L’API reçoit des valeurs absolues sans version de l’état financier ni identifiant métier d’événement. Deux notifications reçues dans l’ordre inverse peuvent faire passer le nombre de parts de 5 à 4 alors que 5 est l’état le plus récent. Le même problème s’applique à une ancienne date d’échéance.

Le conseil « relancer la même commande » après un succès partiel est sûr seulement si aucun état plus récent ne doit être préservé. Il peut devenir dangereux après un autre paiement. L’idempotence d’une valeur identique ne traite pas l’ordre des événements.

**Correction :** distinguer la réparation de propagation d’une nouvelle écriture financière ; identifiant d’opération, séquence/version émise par le système commercial, contrôle de concurrence ou rapprochement avec l’état courant. Ne pas utiliser une règle arbitraire « toujours prendre le maximum » : remboursements et corrections peuvent nécessiter une baisse légitime.

**Tests :** doublon, notification tardive, deux paiements concurrents, remboursement, timeout après écriture, reprise d’une ancienne réponse `partial` après un nouveau paiement.

### A15 — Le client Python n’a pas tous les garde-fous du PHP récent

**Source :** `tools/update_cooperator.py` (70–fin). **Annexe :** PHP 0.4.1 fourni séparément.

`argparse` donne à `--base_url` un défaut non vide égal à `DOMAINE`. Le `args.base_url or os.getenv('base_url') or DOMAINE` du `main` empêche donc normalement la valeur `.env` de s’appliquer lorsque l’option CLI est absente. Une configuration destinée au test peut ainsi viser le domaine par défaut.

Le Python autorise HTTP sans option d’exception spécifique. Ses POST ne désactivent pas explicitement les redirections ; il faut harmoniser ce point avec le transport strict du PHP, surtout pour les identifiants administrateur. Le stockage optionnel des cookies ne force pas de permissions restrictives.

Le PHP joint corrige effectivement plusieurs points précédents. En revanche, la sonde du parseur accepte `--validitydate` inconnu lorsque `--number-shares` est valide : elle obtient parts=3, date=null, code 0. Cette sonde n’a exécuté ni login ni mise à jour. Le risque est ensuite un succès portant sur une demande amputée, non sur la demande de l’appelant.

**Correction :** défaut CLI d’URL à `None`, ordre de priorité documenté, preuve de la destination avant l’envoi ; HTTPS par défaut et redirections sensibles refusées ; cookies privés ; tests CLI négatifs ; contrat identique entre Python, PHP et serveur. Le plafond client de 1 000 000 est maintenant également présent dans le Python au commit audité : ne pas réutiliser la conclusion ancienne selon laquelle il n’y figurait pas.

### A16 — La gestion des prestataires peut modifier une cible d’un autre type

**Source :** `views/manage_provider.py`, branche `update`.

Le rôle de l’appelant est bien vérifié comme administrateur. En revanche, après lecture de l’OID cible, la branche ne vérifie pas que le membre est réellement `MemberTypes.PROVIDER` avant de changer son adresse ou son mot de passe. La liste affichée n’est pas une autorisation du POST.

Il ne s’agit pas d’une élévation d’un membre ordinaire vers administrateur. C’est une exception non contrôlée au périmètre de cette vue, qui peut contredire la règle de lecture seule des fiches d’autres membres.

**Correction :** vérifier le type de la cible et formaliser une opération administrative séparée si la modification d’autres catégories est réellement autorisée. Test négatif avec un coopérateur comme cible, sans aucune écriture.

### A17 — Les budgets LDAP et le coût des traitements ne sont pas suffisamment bornés

**Sources :** `ldap_factory.py`, `utils.py::get_ldap_member_list`, `views/modify_member.py`, `dynamic_groups.py`.

La fabrique ne fixe pas de budget applicatif explicite de connexion et de réception LDAP. Plusieurs parcours dépendent de recherches non paginées ; le scan des appartenances effectue de nombreuses lectures par groupe et par membre. Le client financier charge en outre la page d’annuaire pour obtenir son jeton.

Ce sont des facteurs de blocage et de montée en charge, pas des mesures de lenteur réalisées. Les seuils et limites LDAP du déploiement n’ont pas été relevés.

**Correction :** timeouts explicites, pagination RFC 2696 et contrôle des résultats incomplets, inventaire des appels par parcours, récupération de CSRF via un endpoint léger, métriques de durée et traitement par lots. Maintenir les connexions séparées par appel/requête, correction déjà présente dans le projet.

**Tests :** LDAP qui ne répond plus, limite de taille atteinte, lot plus grand que la limite configurée, gros annuaire, reprise après interruption du scan.

### A18 — La stratégie de test doit davantage traverser les frontières métier

**Sources :** workflows `Tests`, `quality`, `smoke`, `test-stack`, `tests/test_unsubscribe.py`, tests des contributions, résultats des sondes.

La CI est utile et les scénarios navigateur existent : il serait faux de décrire le projet comme dépourvu de tests d’intégration. Mais les scénarios de panne, les modèles réels et les transitions inter-parcours restent insuffisamment couverts. Le cas de la purge illustre le problème : un objet permissif remplace celui dont les setters rendent la production différente.

**Correction :** conserver les tests unitaires rapides, mais ajouter une tranche verticale avec les vrais `Member` et ZODB transactionnelle, une autre avec LDAP de test, et un parcours SSO Keycloak isolé. Ajouter une matrice de pannes et de rejeux. Exiger des assertions sur LDAP, ZODB, le statut de session et les données retournées, pas seulement sur un message de succès ou l’existence d’un appel simulé.

Le seuil global de couverture n’est pas à relever mécaniquement pour masquer cette question. L’objectif prioritaire est l’exécution des branches critiques et des scénarios de désynchronisation, avec des assertions négatives précises.

## 5. Corrections antérieures réellement reconnues

L’audit ne réouvre pas artificiellement les corrections acquises. La protection CSRF globale est présente ; les filtres LDAP inspectés échappent les valeurs concernées ; la validation de certificat est activée quand LDAPS est choisi ; les connexions LDAP ne sont plus partagées globalement ; les cookies portent les attributs de sécurité configurés ; le refresh token SSO est chiffré avant stockage ; les routes financières sont dédiées ; les échecs d’écriture de groupes et les compteurs `failed` Keycloak sont pris en compte par le train 0119.

Le contrôle de ces derniers indicateurs reste à compléter par A09/A10, mais l’ancien défaut d’écriture ignorée a bien été corrigé. Un ensemble de groupes vide n’est pas toujours une erreur : il faut distinguer un ensemble vide vérifié d’une lecture impossible. De même, `updated_fields=[]` est légitime quand les valeurs autoritatives sont déjà identiques.

**Rectification d’un ancien message :** en Python, la chaîne non vide `"0"` est vraie. Le piège de vérité portant sur cette chaîne concernait PHP ; il ne faut pas l’attribuer automatiquement au client Python.

## 6. Exploitation, secrets et éléments non certifiés

Le déploiement Docker inspecté réduit l’exposition de plusieurs services et utilise des restrictions de privilèges. Les dépendances sont installées depuis des fichiers verrouillés ; les actions de CI sont épinglées par SHA. `quality.yml` documente deux exceptions `pip-audit` (`PYSEC-2026-3447`, `GHSA-xmj3-9gf7-h52w`) liées à la chaîne setuptools. Ce sont des dérogations à suivre, pas la preuve que l’application soit compromise. Je n’ai pas exécuté de nouvelle analyse indépendante complète des dépendances ou des images.

Le hash LDAP `{SSHA}` est présenté dans le projet comme un risque accepté de compatibilité. Une migration de stockage de mots de passe doit être planifiée avec les capacités de slapd ; cet audit ne propose pas de casser le bind LDAP. Le diagnostic chiffré opt-in des secrets est également distinct de la fuite en clair A12.

À valider opérationnellement : paramétrage réel de TLS et des proxies, ACL LDAP, politiques Keycloak et mappers, révocation des tokens déjà émis, exposition réseau effective, SMTP/DKIM/DMARC, permissions des volumes, alertes, restauration et rétention. Je n’ai pas testé la conformité juridique, les performances sous charge, l’accessibilité navigateur complète, la qualité linguistique des catalogues ni chaque interaction des applications clientes.

## 7. Plan de traitement proposé

| Lot | Objectif | Constats | Preuve attendue |
|---|---|---|---|
| 1 | Restaurer les invariants d’identité et d’autorité des données | A01–A03 | Tests de comptes inactifs, de cache divergent et de champs internes injectés |
| 2 | Sécuriser les capacités et transitions utilisateur | A04–A08, A16 | Vrais objets, liens consommés, refus SSO hors transaction, panne LDAP sans faux succès |
| 3 | Rendre les propagations et reprises fiables | A09–A11, A14 | Lecture inconnue distincte, outbox/reprise, panne Keycloak puis convergence sans nouvel événement |
| 4 | Fermer les risques d’exploitation et de clients | A12–A13, A15, A17 | Secrets absents des traces, sauvegarde restaurée, destination client vérifiée, timeouts/pagination |
| 5 | Verrouiller les régressions transversales | A18 | Suite de scénarios adverses en CI avec services de test réels |

Aucun numéro de train futur n’est imposé : leur attribution appartient au dépôt. Chaque correction doit inclure le cas rouge sur la révision auditée, le correctif, puis le cas vert, sans réduire le contrôle pour faire passer les tests. Les évolutions de contrat public doivent être documentées en français et en anglais.

### Critères de sortie avant validation d’une nouvelle production automatisée

Un compte désactivé reste désactivé sous tous les modes de connexion. Un succès financier confirme LDAP, pas seulement un objet en mémoire. Un formulaire public ne peut pas choisir les faits internes. Une erreur de lecture ne vaut jamais convergence. Une synchronisation en attente possède un mécanisme de reprise durable. Une purge réelle fonctionne avec le modèle persistant et la politique d’historique. Une archive de sauvegarde est complète et restaurable. Enfin, toute erreur d’entrée ou de destination d’un client est détectée avant l’envoi des identifiants.

## 8. Dossier de preuves et commandes

Le dossier contient `contre_tests_audit.py`, `evidence/extraits.py`, `resultats_contre_tests.json` et `preuves_ci.json`. Aucune information de production ni aucun secret du journal de CI n’est recopié.

Exécution des sondes isolées livrées :

```bash
python contre_tests_audit.py --output resultats.json
```

Relecture des mêmes fonctions depuis un vrai clone, sans importer Pyramid :

```bash
# Vérifier séparément que le clone est bien à la révision auditée.
git -C /chemin/alirpunkto rev-parse HEAD
python contre_tests_audit.py --repo /chemin/alirpunkto --output resultats_clone.json
```

Option pour la sonde du PHP fourni :

```bash
python contre_tests_audit.py --php /chemin/modify_contributor_alirpunkto.php
```

`defect_observed: true` décrit la reproduction du problème recherché. La sonde `CACHE-02` est un contrôle de comportement conforme au contrat « charger si absent », pas une anomalie autonome ; elle est explicitement marquée comme telle dans les résultats. Cela ne signifie pas qu’un test de conformité de l’application est vert. Les sondes n’exécutent pas la pile HTTP, ZODB ni des services réels ; leurs dépendances simulées sont visibles dans le script.

## 9. Références et traçabilité

Toutes les références au code de ce rapport sont relatives à la même base immuable :

```text
https://github.com/michaellaunay/alirpunkto/blob/6f50670bad6a2b5ff20024b53d02be48b5d7a03d/
```

Les chemins et noms de fonctions indiqués dans chaque constat permettent de retrouver les passages, sans dépendre des déplacements ultérieurs sur `master`. Les principales empreintes de blob lues sont :

| Fichier | Blob Git |
|---|---|
| `alirpunkto/utils.py` | `63650e1742c05c77be00ce387aa16413911eb5c9` |
| `alirpunkto/models/member.py` | `d1499ebe1ba046b3877573674ac0c6dea32f3e84` |
| `alirpunkto/views/update_contribution.py` | `027229a9ab2404d71d0b67bc7e720c26cc7cc105` |
| `alirpunkto/views/unsubscribe.py` | `5c5e23d625ec80965e64e48214ac9ac0d4aab509` |
| `alirpunkto/views/check_new_email.py` | `b109d803e8876144f8b507f31c48f10e01ae9f83` |
| `alirpunkto/dynamic_groups.py` | `d5c672c6b76d451f32f6d2180b93c07fbc73fad0` |
| `tools/update_cooperator.py` | `1ea788d820cb111a8f3d5132b3c218d780fc8066` |
| `docker/backup.sh` | `f5edc6f7c4e461eacc3a1e1e2c82142f7032e743` |

**CI consultée :** `Tests` run 40101285729, job Python 3.12 120893780557 ; `smoke` run 40101285657 ; `test-stack` run 40101285664 ; `quality` run 40101285716. Les journaux et résultats sont ceux du 24 octobre 2026, pas une nouvelle exécution demandée par cet audit.

**Référentiels externes consultés**, distincts des sources du projet :

```text
https://www.rfc-editor.org/rfc/rfc9700.html
https://www.keycloak.org/docs-api/latest/javadocs/org/keycloak/storage/user/SynchronizationResult.html
https://ldap3.readthedocs.io/en/latest/connection.html
https://docs.pylonsproject.org/projects/pyramid_tm/en/latest/index.html
```

## Conclusion

La base technique et la discipline de correction sont réelles. Le prochain effort ne doit pas ajouter uniquement des vérifications autour du message `success` : il doit garantir ce que ce message affirme. Le traitement prioritaire porte sur l’autorité des données, les transitions d’identité, la consommation des capacités et la reprise des effets externes. Une fois ces invariants rendus testables et vérifiés avec les objets et services pertinents, les améliorations déjà réalisées sur les clients et la CI auront une portée beaucoup plus solide.
