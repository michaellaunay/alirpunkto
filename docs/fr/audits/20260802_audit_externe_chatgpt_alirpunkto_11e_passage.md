# Audit externe du dépôt (ChatGPT), onzième passage — 2 août 2026

**Provenance.** Onzième passage de l'audit statique externe (ChatGPT,
à la demande de Michaël Launay), sur le commit `777074c2` (train
0078) ; passage précédent sur `3fafc121`, couvrant aussi le commit
documentaire intermédiaire `32f9660a`. Note globale proposée :
**8,8/10** — le plus haut de la série. Au fil des passages : 6,5 → 6,9
→ 6,7 → 7,1 → 7,8 → 8,2 → 8,5 → 8,6 → 8,4 → 8,3 → 8,8.

**Statut.** Contre-expertisé le jour même. Les trois P0 du dixième
passage sont déclarés fermés dans le code, le contrat LDIF centralisé
jugé « sain », les tests transversaux « très satisfaisants », et la
documentation en « forte amélioration » — l'auditeur relève que les
erreurs des trains précédents sont assumées par écrit plutôt que
masquées. Le plafond vers 9/10 est explicitement identifié : **aucune
exécution réussie du smoke test n'est encore observable** — c'est un
réglage de visibilité des Actions côté dépôt (les déclencheurs `push`
et `pull_request` existent), puis un premier run vert. Suggestions
retenues au carnet : le **test fonctionnel de l'émetteur partagé**
(§9 : la parité vérifie les noms, pas la justesse de chaque
correspondance — valeurs distinctives, décodage du flux NUL,
comparaison enregistrement par enregistrement) ; la **réserve
temporelle** sur les versements (§10 : les audits archivés décrivent
des états intermédiaires — c'est précisément le rôle des chapeaux de
provenance de chaque versement) ; la **persistance des sanctions**
(§11, décision de design en cours, trois options présentées au
client) ; et la **sérialisation LDIF** (§12, prochain train de code).

## Suites prévues

Prochain train de code : test fonctionnel de l'émetteur, sérialiseur
LDIF, persistance des sanctions (selon la décision) ; côté
exploitation : rendre les Actions visibles et observer le premier
smoke vert ; puis la CI de la pile de test (P1 items 3-4 — qui
rejoignent la proposition du client d'y adosser des tests de
validation et, à terme, un manuel utilisateur bilingue capturé sur la
pile).

# Texte intégral de l'audit (onzième passage)

# Audit actualisé du dépôt AlirPunkto — onzième passage

**Date :** 2 août 2026
**Dépôt :** `michaellaunay/alirpunkto`
**Branche :** `master`
**Commit examiné :** `777074c25f0c55c58a13cf166945cdde8dfeef77`
**Audit précédent :** `3fafc1215915e0a92c882d19058c9767e1be51be`

## 1. Résumé exécutif

Deux commits ont été ajoutés depuis le passage précédent :

1. un commit documentaire archivant les audits et actualisant les chapitres d'architecture ;
2. un correctif technique fermant les trois ruptures P0 découvertes lors du dixième passage.

Le nouveau train corrige effectivement :

* la double clé `args:` du service LDAP ;
* l'ancienne interface LDIF encore utilisée dans `smoke.yml` ;
* l'ancienne interface LDIF encore utilisée dans `init_test.sh` ;
* la duplication du contrat de transport entre plusieurs appelants ;
* l'absence de validation Compose avant le build.

Le contrat LDIF est désormais centralisé dans
`docker/ldif_records.sh`, utilisé par les trois appelants :
`docker/init.sh`, `docker/init_test.sh`,
`.github/workflows/smoke.yml`.

Le workflow smoke valide maintenant les deux fichiers Compose avec
`docker compose config --quiet` avant de construire une image.

Sept nouveaux tests cherchent à empêcher le retour de ces régressions.
Le commit déclare 1 022 tests réussis et une couverture de 72,10 %.

Le connecteur GitHub ne retourne cependant toujours aucun statut ni
aucune exécution de workflow pour ce SHA. L'implantation et le câblage
sont donc vérifiés statiquement, mais la réussite réelle du smoke test
reste non confirmée.

## 2. Évaluation actualisée

| Domaine                           | Note précédente | Nouvelle note |
| --------------------------------- | --------------: | ------------: |
| Architecture applicative          |             8,0 |           8,1 |
| Qualité du code                   |             8,3 |           8,4 |
| Tests unitaires et structurels    |             9,2 |           9,4 |
| CI et tests d'intégration         |             7,8 |           8,9 |
| Documentation                     |             8,0 |           8,6 |
| Dépendances et reproductibilité   |             9,4 |           9,4 |
| Sécurité applicative              |             9,1 |           9,1 |
| Sécurité et fonctionnement Docker |             7,5 |           9,0 |
| Exploitation et observabilité     |             7,5 |           7,6 |

**Note globale actualisée : 8,8/10**, contre 8,3/10 précédemment.

La note ne dépasse pas encore 9/10, principalement parce que le smoke
test n'est toujours pas observable comme ayant réellement réussi.

# 3. Compose de production — P0 résolu

Le service LDAP possède désormais un seul bloc `args`
(`BUILD_WITH_DEBUG` + `UBUNTU_SNAPSHOT`). La double clé YAML a
disparu. Les deux arguments atteignent donc le même build :
l'activation éventuelle des outils de diagnostic et l'épinglage
facultatif du dépôt Ubuntu sur un snapshot.

**Statut : résolu.**

# 4. Validation Compose avant le build — résolu par câblage

Le workflow smoke contient maintenant une étape dédiée avant la
construction, qui valide les deux fichiers Compose avec
`config --quiet`.

Cette étape détectera notamment : les erreurs YAML comprises par
Compose ; les clés dupliquées rejetées par son parseur ; les
substitutions de variables invalides ; les références de services
incohérentes ; plusieurs erreurs structurelles de configuration.

L'ordre est correct : la validation précède « Build the images ».

Les tests vérifient également l'existence de deux appels à
`config --quiet`, leur position avant le build, et l'absence de clés
dupliquées dans les deux fichiers Compose.

**Statut : résolu par inspection.**

**Réserve.** Le détecteur Python ajouté dans les tests est un
analyseur minimal adapté au YAML en blocs utilisé par le projet, pas
un parseur YAML complet. Ce n'est pas bloquant, car la CI doit
également exécuter le véritable parseur de Docker Compose. En
revanche, faute d'exécution visible, seule la partie statique est
aujourd'hui démontrée.

# 5. Contrat LDIF centralisé — résolu

Le flux d'enregistrements NUL n'est plus défini directement dans
`init.sh`. Il est centralisé dans `docker/ldif_records.sh`, qui expose
une seule fonction, `generate_ldif_records`. Elle émet les 25 champs
obligatoires et les 8 champs facultatifs attendus par
`generate_ldif.py`. Les valeurs obligatoires absentes sont émises
vides, puis rejetées par le générateur, qui reste l'autorité unique de
validation.

Cette séparation est saine : le shell adapte les noms de variables des
différents appelants ; le générateur vérifie le protocole ; le
générateur refuse les champs absents, vides ou inconnus ; le
générateur effectue seul le hachage des mots de passe.

**Statut : résolu.**

# 6. docker/init.sh — migré correctement

L'initialisation de production crée explicitement l'alias attendu
(`ADMIN_UUID="${LDAP_ADMIN_OID}"`), puis charge l'émetteur et utilise
uniquement les deux chemins sur la ligne de commande. Le contrat de
production est donc cohérent avec celui du générateur.

**Statut : résolu.**

# 7. docker/init_test.sh — migré correctement

Le script de test ne calcule plus lui-même de hashes `{SSHA}`. Il
définit maintenant les valeurs canoniques attendues par l'émetteur
(compte administrateur ; premier utilisateur ; second utilisateur ;
rôles ; langues ; nationalités ; descriptions ; date courante), charge
le contrat partagé et transmet les enregistrements sur l'entrée
standard. Les UUID et mots de passe nécessaires sont initialisés au
début du script, avec des valeurs locales par défaut ou des valeurs
fournies dans l'environnement.

**Statut : résolu par inspection.**

**Réserve.** Le workflow smoke ne lance pas réellement
`docker/init_test.sh` — il reproduit son propre setup non interactif.
La compatibilité de `init_test.sh` est donc protégée par des tests
structurels, mais son exécution complète reste à tester : génération
du LDIF ; génération du certificat ; création ou normalisation de
`test.ini` ; lancement de la pile locale.

# 8. Workflow smoke — interface LDIF réparée

Le workflow ne référence plus `GENERATE_LDIF_ADMIN_PW`,
`GENERATE_LDIF_U1_PW`, `GENERATE_LDIF_U2_PW`. Il définit les variables
canoniques, charge l'émetteur partagé et appelle le générateur avec
les deux chemins autorisés.

Le workflow redevient donc capable, en principe, d'atteindre les
étapes suivantes : validation Compose ; construction des images ;
création d'un certificat temporaire ; démarrage de la pile ; requête
HTTPS à travers Apache ; test de transmission de l'adresse cliente à
Waitress ; diagnostic et nettoyage.

**Statut : réparé par inspection.**

**Preuve d'exécution manquante.** Pour le commit `777074c…`, le
connecteur ne retourne aucun statut combiné ni aucune exécution de
workflow associée. Cela ne prouve pas nécessairement qu'aucun workflow
n'a été lancé, car le connecteur d'exécutions est limité dans sa
couverture. Cela signifie néanmoins qu'aucune réussite ne peut être
attestée à partir des données disponibles ici. Le P0 de code est
fermé ; la validation opérationnelle reste en attente de preuve.

# 9. Tests transversaux des appelants — nette amélioration

Le nouveau fichier `tests/test_ldif_callers.py` couvre les trois
appelants connus (`docker/init.sh`, `docker/init_test.sh`,
`.github/workflows/smoke.yml`).

Les tests vérifient : l'absence de clés Compose dupliquées ; la
présence des deux arguments de build LDAP ; l'utilisation de
l'émetteur partagé par chaque appelant ; l'absence des anciennes
variables `GENERATE_LDIF_*` ; l'absence d'arguments utilisateur après
les deux chemins ; la parité entre les champs émis et les champs
déclarés par le générateur ; l'absence de hachage de mot de passe dans
les scripts shell ; la présence de la validation Compose avant le
build.

**Statut : très satisfaisant.**

**Limite des contrôles structurels.** La parité vérifie les noms
d'enregistrements, mais pas la justesse de chaque correspondance. Par
exemple, une erreur telle que `emit U1_NAT "${USER1_LANG}"`
conserverait le bon ensemble de noms tout en envoyant une mauvaise
valeur. Les correspondances actuelles sont correctes par inspection,
mais un petit test fonctionnel de l'émetteur partagé renforcerait le
contrat : 1. définir des valeurs distinctives pour toutes les
variables ; 2. exécuter `generate_ldif_records` ; 3. décoder le flux
NUL ; 4. comparer chaque enregistrement à la variable source attendue.

# 10. Documentation — mise à jour importante

Le commit intermédiaire `32f9660…` archive les audits antérieurs en
français et en anglais, puis actualise notamment les chapitres
relatifs aux groupes LDAP, à l'authentification, à la sécurité, aux
tests et au déploiement Docker.

La documentation reconnaît les contre-revues et les surévaluations
antérieures, notamment l'affirmation prématurée selon laquelle le P2
était fermé. Cette traçabilité est positive : l'historique des
décisions, corrections et limites n'est pas réécrit comme si les
erreurs n'avaient jamais existé.

**Statut : forte amélioration.**

**Réserve temporelle.** Les documents archivés décrivent
nécessairement des états intermédiaires. Ils doivent rester clairement
présentés comme des audits historiques et non comme la situation
actuelle du dépôt.

# 11. Réserve importante : persistance d'une nouvelle sanction

Le correctif précédent a rendu le côté membre autoritatif afin
d'éviter qu'une ancienne sanction ou un ancien rôle présent uniquement
sur le groupe soit restauré. Ce choix ferme correctement le risque de
résurrection d'un état révoqué.

Cependant, le scénario inverse reste ouvert :

1. une nouvelle sanction est calculée avec `force_sanctioned=True` ;
2. l'ajout côté groupe réussit ;
3. l'ajout côté membre échoue ;
4. le prochain passage lit le côté membre sans sanction ;
5. l'enregistrement restant côté groupe est considéré comme obsolète ;
6. la sanction peut être retirée au lieu d'être rejouée.

L'ordre fail-closed protège l'application immédiatement : elle ne lit
pas une sanction tant que le membre ne la porte pas. Mais cela
signifie justement que l'utilisateur peut ne pas être sanctionné si
l'écriture autoritative échoue.

**Recommandation.** Les sanctions devraient disposer d'un état
autoritatif indépendant des groupes dérivés, par exemple : attribut
LDAP dédié ; enregistrement applicatif persistant ; journal
d'événements ; file de reprise transactionnelle. La fonction devrait
également retourner les opérations réellement appliquées, et non
seulement la cible théorique calculée.

**Statut : ouvert, sévérité moyenne à élevée.**

# 12. Sérialisation LDIF — toujours à durcir

Le transport vers Python est maintenant sûr vis-à-vis de `argv`. En
revanche, certaines valeurs sont encore incorporées directement dans
le LDIF (`f"sn: {last}"`, `f"cn: {pseudonym}"`,
`f"givenName: {first}"`, `f"description: {description}"`,
`f"mail: {email}"`).

Une valeur contenant `\r` ou `\n` pourrait modifier la structure du
document LDIF. Le chemin interactif limite naturellement ce risque,
mais `generate_ldif.py` est maintenant une interface autonome
alimentée par `stdin`.

**Correction recommandée.** Créer un sérialiseur commun qui : refuse
les NUL et retours à la ligne dans les champs mono-ligne ; encode en
base64 les valeurs exigées par LDIF ; valide les UUID ; limite les
rôles aux valeurs autorisées ; valide les codes de langue et de
nationalité ; valide les dates et adresses électroniques.

**Statut : ouvert.**

# 13. Autres constats restant ouverts

**LDAP chiffré par défaut.** Les connexions LDAPS valident
correctement les certificats, mais les piles fournies utilisent encore
LDAP clair sur le port 389.

**Coût du scan des groupes.** Le scan périodique continue d'effectuer
de nombreuses lectures LDAP par membre et par groupe. Une lecture
globale suivie d'une table inverse réduirait fortement le coût.

**Tâches périodiques dans NewRequest.** Les rappels restent liés au
trafic HTTP et au processus Pyramid : aucune exécution sans trafic ;
risque de doublons multiprocessus ; absence de planification externe
fiable.

**.env.example.** Le modèle conserve encore des incohérences sur les
noms des variables mail et ne présente pas complètement la
configuration LDAPS.

**Tests Docker locaux.** La pile de test installe encore ses
dépendances supplémentaires au démarrage du conteneur. Une image de
test dédiée serait plus autonome et plus déterministe.

**Reproductibilité APT.** Le mode snapshot existe, mais reste
facultatif. Les builds sans `ALIRPUNKTO_UBUNTU_SNAPSHOT` continuent à
utiliser l'archive Ubuntu mouvante.

**Qualité progressive.** mypy reste non bloquant ; Ruff est limité à
la famille F ; `F841` reste ignorée ; le seuil de couverture reste à
68 % ; Certbot réel et renouvellement ne sont pas testés ; la CSP
n'est pas activée et testée.

# 14. Priorités révisées

**P0 — fermé dans le code** : Compose sans clé dupliquée ; workflow
smoke migré ; setup local migré ; validation Compose avant build ;
contrat LDIF partagé. La réussite réelle du workflow smoke reste à
observer.

**P1 — validation d'intégration** : 1. obtenir une exécution GitHub
Actions visible et réussie ; 2. vérifier les étapes Compose, build,
healthchecks, Apache et throttle ; 3. exécuter `init_test.sh` dans un
environnement propre ; 4. démarrer réellement la pile locale de test ;
5. tester fonctionnellement les correspondances de l'émetteur partagé.

**P2 — cohérence et sécurité LDAP** : 1. rendre les sanctions
persistantes malgré un échec partiel ; 2. introduire une source
autoritative distincte pour les états institutionnels ; 3. sérialiser
correctement les valeurs LDIF ; 4. activer et tester LDAPS dans les
piles fournies ; 5. optimiser le scan des relations de groupes.

**P3 — exploitation** : 1. sortir les tâches périodiques de
`NewRequest` ; 2. corriger `.env.example` ; 3. rendre le snapshot APT
obligatoire pour les images publiées ; 4. produire une image de test
autonome ; 5. tester Certbot et la CSP.

# 15. Conclusion

Le commit `777074c…` ferme correctement les trois ruptures P0
découvertes lors du passage précédent.

Les gains les plus importants sont : retour à un Compose de production
valide ; restauration du workflow smoke ; restauration du setup local
de test ; contrat LDIF partagé par tous les appelants ; contrôle
transversal des migrations d'interface ; validation Compose
positionnée avant toute construction.

La qualité de la réaction est également à souligner : les commentaires
et la documentation reconnaissent explicitement les défauts introduits
par les trains précédents plutôt que de les masquer.

Le dépôt présente maintenant : une chaîne Python fortement
verrouillée ; une image Pyramid propre et minimale ; une sécurité
applicative nettement améliorée ; une CI bien conçue sur le papier ;
une couverture structurelle élevée.

Les principaux écarts restants sont désormais moins nombreux mais plus
spécialisés : absence de preuve d'exécution du smoke test ;
persistance des sanctions lors d'un échec partiel ; sérialisation
LDIF ; LDAPS non activé par défaut ; tâches périodiques et qualité
encore progressives.

**Évaluation actuelle : 8,8/10.**

Une exécution smoke observable et réussie, suivie du durcissement LDIF
et de la persistance des sanctions, permettrait de franchir
durablement le seuil de 9/10.
