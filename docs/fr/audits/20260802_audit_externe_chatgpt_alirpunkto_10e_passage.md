# Audit externe du dépôt (ChatGPT), dixième passage — 2 août 2026

**Provenance.** Dixième passage de l'audit statique externe (ChatGPT,
à la demande de Michaël Launay), sur le commit `3fafc121` (train
0076) ; passage précédent sur `72e65db2`. Note globale proposée :
**8,3/10** — en baisse pour la deuxième fois. Au fil des passages :
6,5 → 6,9 → 6,7 → 7,1 → 7,8 → 8,2 → 8,5 → 8,6 → 8,4 → 8,3.

**Statut.** Contre-expertisé le jour même : les quatre corrections de
sécurité du 0076 sont validées, et **les trois P0 signalés sont
fondés — et de notre fait**. La double clé `args:` vient de
l'insertion 0075 devant un bloc existant que l'inspection n'affichait
pas, et le contrôle « YAML OK » était un faux vert (PyYAML avale les
clés dupliquées là où compose refuse le fichier) ; `smoke.yml` est
resté sur l'ancienne interface parce que le grep de migration 0076
s'arrêtait à `tests/ docker/` sans `.github/` ; `init_test.sh` n'avait
jamais été migré — et son `hash_ssha` poussait de surcroît chaque mot
de passe dans l'argv du python de hachage. Le §11 est la leçon : les
tests inspectaient *un* appelant, pas *les* appelants. Corrections
livrées par 0078 (mergé `777074c2`) : émetteur commun
`docker/ldif_records.sh` sourcé par les trois appelants, doublon
fusionné, porte `compose config --quiet` sur les deux fichiers,
sept tests transversaux — évaluées par le onzième passage (8,8). La
réserve de formulation du §3 (« un pipe visible par personne ») est
également corrigée dans les commentaires. Restent ouverts et suivis :
la **persistance d'une nouvelle sanction** (§7, décision de design en
cours — trois options sur la table) et la **sérialisation LDIF** (§12,
prochain train de code).

## Suites données

0078 (P0 + P1-cohérence, chronique dans le versement du 11ᵉ passage) ;
à venir : sanctions (P2, décision), sérialiseur LDIF, LDAPS (décision
d'exploitation), optimisation du scan, reminder hors HTTP,
`.env.example`.

# Texte intégral de l'audit (dixième passage)

# Audit actualisé du dépôt AlirPunkto — dixième passage

**Date :** 2 août 2026
**Dépôt :** `michaellaunay/alirpunkto`
**Branche :** `master`
**Commit examiné :** `3fafc1215915e0a92c882d19058c9767e1be51be`
**Audit précédent :** `72e65db2de566bc193c5d14130ac301594b4231a`

## 1. Résumé exécutif

Le nouveau commit corrige correctement les quatre réserves de sécurité
formulées lors du passage précédent :

* toutes les données utilisateur destinées au LDIF quittent désormais `argv` ;
* une donnée obligatoire manquante ou vide fait échouer la génération ;
* les écritures LDAP par paires sont réellement conditionnelles ;
* le côté membre devient la source autoritative pour les rôles, sanctions et appartenances persistantes.

Ces corrections sont accompagnées de tests ciblés injectant des échecs
LDAP et des entrées LDIF invalides.

Cependant, l'intégration Docker reste actuellement bloquée par **trois
problèmes P0** :

1. `docker/docker-compose.yaml` contient toujours deux clés `args:` dans le service LDAP ;
2. le workflow `smoke.yml` utilise encore l'ancienne interface positionnelle de `generate_ldif.py` ;
3. `docker/init_test.sh` utilise lui aussi l'ancienne interface.

Le workflow smoke et l'environnement local de test échoueront donc
avant de pouvoir tester la pile. Le P0 Docker reste ouvert.

Le commit annonce 1 015 tests réussis et une couverture de 72,10 %. Le
connecteur GitHub ne remonte toutefois aucun statut ni workflow
associé à ce SHA. Ces résultats sont donc déclarés par le commit, mais
non confirmés indépendamment.

## 2. Évaluation actualisée

| Domaine                           | Note précédente | Nouvelle note |
| --------------------------------- | --------------: | ------------: |
| Architecture applicative          |             7,9 |           8,0 |
| Qualité du code                   |             8,1 |           8,3 |
| Tests unitaires et structurels    |             9,1 |           9,2 |
| CI et tests d'intégration         |             8,8 |           7,8 |
| Documentation                     |             8,0 |           8,0 |
| Dépendances et reproductibilité   |             9,4 |           9,4 |
| Sécurité applicative              |             8,8 |           9,1 |
| Sécurité et fonctionnement Docker |             7,9 |           7,5 |
| Exploitation et observabilité     |             7,5 |           7,5 |

**Note globale actualisée : 8,3/10**, contre 8,4/10 précédemment.

La sécurité applicative progresse nettement, mais les ruptures du
workflow smoke et du setup de test local empêchent de valoriser
pleinement ces corrections.

# 3. Transport LDIF intégral par l'entrée standard — résolu

Le générateur n'accepte désormais que deux arguments :
`generate_ldif.py TEMPLATE OUT`. Toutes les autres données sont reçues
sur l'entrée standard sous forme d'enregistrements `NOM=VALEUR\0`.

Les données concernées incluent désormais : mots de passe ; UUID ;
identifiants ; pseudonymes ; rôles ; noms et prénoms ; adresses
électroniques ; langues ; nationalités ; dates de naissance ;
descriptions.

Le script de production construit ces enregistrements avec `printf` et
les transmet par un pipe :

```bash
generate_ldif_records | python3 docker/generate_ldif.py \
    "${LDIF_TEMPLATE}" "${LDIF_OUT}"
```

La ligne de commande ne contient plus que les chemins du modèle et du
fichier de sortie. Cela supprime l'exposition permanente dans
`/proc/<pid>/cmdline` ainsi que l'exposition par les outils classiques
d'affichage des processus.

**Statut : résolu.**

**Réserve de formulation.** Le commentaire affirme qu'un pipe est
« visible par personne ». Ce n'est pas strictement exact : un
administrateur root, un débogueur autorisé ou un processus disposant
de droits de traçage peut toujours observer la mémoire ou les
descripteurs d'un processus. Le mécanisme est néanmoins nettement plus
sûr que `argv`, l'environnement ou un fichier temporaire persistant.

# 4. Champs obligatoires et mots de passe vides — résolu

Le générateur définit explicitement 25 champs obligatoires et 8 champs
facultatifs. Avant toute écriture, il recherche les champs absents ou
vides :

```python
_missing = sorted(
    name for name in REQUIRED_FIELDS
    if not _fields.get(name)
)
```

Une erreur provoque l'arrêt avant la création du LDIF. Les noms
d'enregistrements inconnus provoquent également un échec.

Les tests vérifient : l'absence d'un mot de passe ; un mot de passe
vide ; un nom de champ inconnu ; l'absence du fichier LDIF après
l'échec ; le caractère facultatif des dates et descriptions.

Le risque de créer silencieusement un compte dont le mot de passe
serait vide est fermé.

**Statut : résolu.**

# 5. Écritures LDAP réellement « fail-closed » — résolu pour les cas testés

L'ancienne version ordonnait correctement les écritures mais ignorait
le résultat de la première opération. La nouvelle version conditionne
réellement la seconde écriture.

*Ajout d'une appartenance* : 1. ajout sur le groupe ; 2. ajout sur le
membre uniquement si le premier ajout réussit.

*Suppression d'une appartenance* : 1. suppression sur le membre ;
2. suppression sur le groupe uniquement si la première suppression
réussit.

Les tests injectent un refus précis dans `conn.modify()` et
vérifient : qu'un échec de l'ajout côté groupe bloque l'ajout côté
membre ; qu'un échec de la suppression côté membre empêche la
suppression côté groupe.

**Statut : résolu pour la propagation immédiate des écritures.**

# 6. Côté membre autoritatif — correction cohérente

La table de vérité utilisait précédemment
`current = member_side | group_side`. Un enregistrement périmé présent
uniquement sur le groupe pouvait ainsi restaurer une sanction levée,
un rôle Board supprimé ou un rôle MAC supprimé.

Le calcul utilise désormais uniquement `current = member_side`.

Les tests vérifient que : un ancien rôle Board restant uniquement sur
le groupe est supprimé ; une ancienne sanction restant uniquement sur
le groupe n'est pas restaurée.

Ce choix est cohérent avec l'application, qui lit le côté membre pour
déterminer les droits.

**Statut : résolu pour les révocations incomplètes.**

# 7. Réserve persistante : perte possible d'une nouvelle sanction

Le côté membre contient désormais l'état autoritatif des sanctions et
des rôles persistants. La table de vérité détermine notamment la
sanction à partir de `current & {SANCTIONED, SANCTIONED_MISSING_YEAR}`
sauf lorsque l'événement fournit explicitement `force_sanctioned`.

Un scénario reste problématique :

1. un événement applique une nouvelle sanction avec `force_sanctioned=True` ;
2. l'écriture côté groupe réussit ;
3. l'écriture côté membre échoue ;
4. la fonction journalise l'échec, mais retourne néanmoins la cible calculée ;
5. au passage suivant, le côté membre ne porte aucune sanction ;
6. la sanction présente uniquement sur le groupe est considérée comme périmée et supprimée.

Le commentaire considère qu'une attribution perdue est « sûre et
rejouable ». Cette hypothèse convient à un privilège supplémentaire,
mais pas forcément à une sanction, qui est au contraire une
restriction de droits.

La nouvelle architecture privilégie donc correctement la sécurité lors
d'une révocation, mais ne garantit pas la persistance d'une nouvelle
sanction en cas d'échec de l'écriture autoritative.

**Recommandation.** Les sanctions et les rôles institutionnels
devraient être stockés dans des attributs LDAP dédiés, indépendants
des groupes dérivés. À défaut : retourner un résultat structuré
indiquant les écritures réellement réussies ; placer l'opération en
file de reprise ; réessayer explicitement la sanction tant que le côté
membre ne la contient pas ; ne pas retourner simplement la cible
théorique après un échec.

**Statut : ouvert, sévérité moyenne à élevée selon l'usage des
sanctions.**

# 8. P0 : Compose de production toujours invalide

Le service LDAP contient toujours deux clés `args:` au même niveau.
Selon le parseur YAML, le fichier sera refusé à cause de la clé
dupliquée, ou le second bloc remplacera le premier. Dans le second
cas, le snapshot Ubuntu ne sera jamais transmis au build OpenLDAP.

**Correction requise** : fusionner en un seul bloc
`args: {BUILD_WITH_DEBUG, UBUNTU_SNAPSHOT}`.

**Contrôle obligatoire** : `docker compose --env-file docker/.env -f
docker/docker-compose.yaml config --quiet`.

**Statut : ouvert, P0.**

# 9. P0 : workflow smoke incompatible avec le nouveau générateur

Le workflow smoke utilise encore `GENERATE_LDIF_ADMIN_PW`,
`GENERATE_LDIF_U1_PW`, `GENERATE_LDIF_U2_PW`, les tirets de
remplacement et l'ancienne longue liste d'arguments positionnels. Or
le générateur refuse désormais toute invocation dont la ligne de
commande ne contient pas exactement deux chemins.

Le workflow s'arrêtera donc pendant l'étape « Generate a throwaway
stack configuration », avant la validation de Compose, le build des
images, le démarrage de la pile, le test Apache et le test du proxy
Waitress. Il ne peut actuellement pas remplir son objectif.

**Correction nécessaire.** La génération dans le workflow doit
utiliser le même contrat que `init.sh` (fonction `emit`, pipe vers le
générateur avec les deux chemins seuls), et ajouter, avant le build,
`${COMPOSE_CMD} config --quiet`.

**Statut : ouvert, P0.**

# 10. P0 : initialisation locale de test également cassée

`docker/init_test.sh` continue à : 1. hacher les mots de passe
lui-même ; 2. appeler `generate_ldif.py` avec l'ancienne interface
positionnelle ; 3. transmettre les données utilisateur dans `argv`.

Le générateur refusera cette invocation pour le même motif que le
workflow smoke. La commande documentée `./docker/init_test.sh` ne peut
donc plus produire `docker/initials_users.test.generated.ldif`. La
pile locale de tests n'est plus initialisable par le chemin prévu.

**Correction nécessaire.** Extraire la génération des enregistrements
NUL dans un outil commun utilisé par `docker/init.sh`,
`docker/init_test.sh` et `.github/workflows/smoke.yml`. Cela évitera
de maintenir trois copies du même contrat.

**Statut : ouvert, P0.**

# 11. Couverture de tests insuffisante sur les appelants du générateur

Les tests du transport inspectent uniquement `docker/init.sh`. Ils
vérifient correctement que cet appelant n'utilise plus l'ancien
contrat. Ils n'inspectent toutefois pas `docker/init_test.sh`,
`.github/workflows/smoke.yml`, ni les autres scripts ou exemples
documentaires.

Le changement d'interface a donc cassé deux appelants sans provoquer
d'échec dans la suite déclarée.

**Test structurel recommandé.** Rechercher tous les appels au
générateur et exiger : exactement deux arguments après le nom du
script ; une alimentation par `stdin` ; aucune référence
`GENERATE_LDIF_*` ; aucune liste positionnelle historique. Un test
plus robuste exécuterait directement `docker/init_test.sh` en mode non
interactif, l'étape de préparation du workflow smoke et
`docker compose config --quiet`.

# 12. Sérialisation LDIF à durcir

Le transport NUL protège correctement les valeurs entre Bash et
Python. Cependant, le générateur insère encore plusieurs valeurs
directement dans des lignes LDIF (`f"sn: {last}"`,
`f"cn: {pseudonym}"`, `f"givenName: {first}"`,
`f"description: {description}"`, `f"mail: {email}"`).

Une valeur contenant un retour à la ligne peut modifier la structure
du LDIF ou injecter un nouvel attribut. `init.sh` collecte
actuellement les valeurs ligne par ligne, ce qui limite le risque dans
le chemin interactif normal, mais le générateur accepte maintenant
directement des valeurs arbitraires sur `stdin`.

**Recommandation.** Utiliser une fonction de sérialisation LDIF qui :
refuse `\0`, `\r` et `\n` dans les champs simples ; encode en base64
les valeurs qui l'exigent ; valide les UUID, rôles, langues et
nationalités ; valide les adresses électroniques et dates avant
écriture.

**Statut : ouvert, durcissement moyen.**

# 13. Constats antérieurs toujours ouverts

**LDAP chiffré.** Les certificats LDAPS sont correctement validés
lorsqu'il est activé, mais les piles fournies utilisent toujours LDAP
clair sur le port 389.

**Performances du scan LDAP.** Le scan charge les appartenances avec
plusieurs recherches par membre et par groupe. Une table inverse
chargée en une passe serait préférable pour un grand annuaire.

**Tâches périodiques.** Les rappels restent déclenchés depuis
`NewRequest`, sans garantie d'exécution sans trafic ni coordination
multiprocessus.

**.env.example.** Le fichier conserve des variables mail obsolètes et
ne documente pas correctement la configuration LDAPS.

**Chaîne d'image.** L'image Pyramid est bien finalisée, mais restent :
le snapshot APT facultatif ; l'installation dynamique des dépendances
de tests au démarrage de la pile locale ; l'absence de smoke test
observé avec succès.

**Dette qualité.** mypy reste non bloquant ; Ruff reste limité aux
règles `F` ; `F841` est ignorée ; le seuil de couverture reste à
68 % ; Certbot et la CSP ne sont pas testés.

# 14. Priorités révisées

**P0 — intégration Docker.** 1. Fusionner les deux blocs `args` du
service LDAP. 2. Migrer `smoke.yml` vers le transport NUL sur
`stdin`. 3. Migrer `init_test.sh` vers le même contrat. 4. Ajouter
`docker compose config --quiet`. 5. Exécuter le smoke test complet
dans GitHub Actions. 6. Vérifier le résultat du build et de la requête
HTTPS traversant Apache.

**P1 — cohérence des outils.** 1. Créer un générateur commun de flux
LDIF. 2. Tester tous les appelants de `generate_ldif.py`. 3. Exécuter
réellement le setup de test dans la CI. 4. Valider les deux fichiers
Compose avec un parseur strict.

**P2 — cohérence LDAP.** 1. Garantir la persistance des nouvelles
sanctions après un échec partiel. 2. Retourner l'état réel des
écritures, pas seulement la cible calculée. 3. Introduire une reprise
ou une file de réconciliation. 4. Stocker sanctions et rôles
institutionnels dans des attributs autoritatifs.

**P3 — durcissement.** 1. Sérialiser proprement les valeurs LDIF.
2. Activer et tester LDAPS dans Compose. 3. Optimiser le scan LDAP.
4. Sortir les tâches périodiques du cycle HTTP. 5. Corriger
`.env.example`.

# 15. Conclusion

Le commit `3fafc12…` corrige correctement les constats de sécurité
portant sur : l'exposition des données personnelles dans `argv` ; les
mots de passe manquants ou vides ; la propagation d'écritures après un
premier échec ; la restauration involontaire de rôles révoqués.

Ces corrections font progresser sensiblement la sécurité du code
applicatif.

Cependant, la migration de l'interface LDIF n'a pas été propagée à
tous ses appelants. Le workflow smoke et le setup local de test sont
désormais incompatibles avec le générateur. En parallèle, le Compose
de production conserve sa double clé `args`.

Le dépôt possède donc actuellement : une bonne sécurité applicative ;
une image de production bien construite ; des tests unitaires
solides ; mais une chaîne d'intégration Docker non fonctionnelle par
inspection statique.

**Évaluation actuelle : 8,3/10.**

Après correction du Compose, migration des deux appelants LDIF et
réussite observable du smoke test, la note pourrait atteindre environ
**8,9/10**.

La prochaine mise à jour devra d'abord vérifier les trois corrections
P0 et rechercher une exécution smoke réellement réussie.
