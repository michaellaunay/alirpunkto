# Audit externe du dépôt (ChatGPT), huitième passage — 2 août 2026

**Provenance.** Huitième passage de l'audit statique externe (ChatGPT,
à la demande de Michaël Launay), sur le commit `2bc56291` (transport
LDIF par slots d'environnement et réconciliation des groupes) ; passage
précédent (le septième, noté 8,5 sur `2c53ef8b`, texte non transmis).
Note globale proposée : **8,6/10**. Au fil des passages : 6,5 → 6,9 →
6,7 → 7,1 → 7,8 → 8,2 → 8,5 → 8,6. Le texte intégral est reproduit en
seconde partie de ce document.

**Statut.** Contre-expertisé le jour même : **les quatre constats
portés contre le train 0074 sont fondés**, et le reproche liminaire —
le message de commit affirmait « ceci clôt le P2 » à tort — est
assumé. Ils sont corrigés par le patch 0076 (mergé en `3fafc121`).
Précision de calendrier : la section « Image » des constats antérieurs
(§11) décrit l'état *avant* le merge du train de finition d'image
(0075, `72e65db2`), qui couvre déjà la wheel applicative,
`--only-binary`, le contexte réduit et le mécanisme de snapshot APT.

## Contre-expertise

- **§4, données personnelles dans `argv`** : fondé. Le train 0074
  avait jugé pseudonymes, rôles, langues et nationalités « identifiants,
  pas données personnelles » — c'était une erreur d'appréciation, la
  nationalité en particulier. Correction 0076 : l'interface
  positionnelle disparaît pour toute donnée utilisateur ; la ligne de
  commande ne porte plus que les deux chemins de fichiers, toutes les
  valeurs transitent en enregistrements `NOM=VALEUR` délimités par NUL
  sur l'entrée standard du générateur (un tube n'est visible de
  personne, ne touche aucun disque, transporte tout octet).
- **§5, variable de mot de passe absente** : fondé — et grave en cas
  de mauvais usage direct du générateur : `os.environ.pop(nom, "")`
  faisait du mot de passe oublié le hash `{SSHA}` *valide* de la chaîne
  vide. Correction 0076 : un champ requis manquant **ou vide** fait
  avorter le générateur avec la liste des noms manquants, avant toute
  écriture ; un nom d'enregistrement inconnu avorte aussi (une faute de
  frappe doit échouer bruyamment).
- **§7, « fail-closed » non appliqué** : fondé — l'ordre des écritures
  était correct mais le retour de `_checked_modify` ignoré : la seconde
  écriture suivait un échec de la première. Correction 0076 : la
  seconde écriture de chaque paire est conditionnelle (octroi côté
  membre seulement si le côté groupe porte l'enregistrement ;
  révocation côté groupe seulement si le côté membre est propre).
- **§8, l'union ressuscite un état obsolète** : fondé — le scénario de
  résurrection d'un rôle Board/CMA ou d'une sanction à moitié levée
  était réel (« réparé dans le mauvais sens »). Correction 0076 : le
  côté **membre** (ce que lit l'application) est l'état courant
  autoritatif ; un enregistrement de groupe en retard converge vers le
  bas. L'asymétrie qui en résulte est volontaire et documentée : un
  octroi dont la moitié membre a échoué est roulé en arrière au passage
  suivant (perdre un octroi est sûr et rejouable), une révocation
  converge jusqu'à ce que les deux côtés soient propres.
- **§9, coût du scan** (membres × groupes) : fondé, retenu comme
  optimisation P3 (groupes chargés une fois, table inverse, recherche
  paginée).
- **§10, tests manquants** : les cas listés existent depuis 0076 —
  vetos d'écriture ciblés (octroi groupe échoué, révocation membre
  échouée), latch Board et sanction à moitié levés non ressuscités,
  mot de passe absent et vide, `argv` réduit aux deux chemins.

## Décisions actées (rappel)

Inchangées. S'y ajoute la question posée par l'auditeur en P3 :
**activer LDAPS dans la pile compose** — le mécanisme validant est prêt
depuis 0073 (`Tls` + `LDAP_CA_CERT_FILE`), l'activation et
l'outillage certificats du conteneur LDAP restent une décision
d'exploitation du client.

## Suites données et restantes

- **0076** (mergé `3fafc121`) : ferme les items 1 à 4 du « P2 à
  terminer » et fournit les tests de l'item 5.
- **P3 exploitation** (à venir) : LDAPS compose (décision client),
  optimisation du scan, sortie des rappels du cycle HTTP,
  `.env.example`.
- **P4** : mypy progressivement bloquant, Ruff élargi, plancher de
  couverture relevé, Certbot et CSP testés. Les deux premiers items
  listés par l'auditeur (wheel applicative, APT figé) étaient déjà
  couverts par 0075, mergé après son examen.

# Texte intégral de l'audit (huitième passage)

# Audit actualisé du dépôt AlirPunkto — huitième passage

**Date :** 2 août 2026
**Dépôt :** `michaellaunay/alirpunkto`
**Branche :** `master`
**Commit examiné :** `2bc562912856a20a777d38b748bece8b41916c97`
**Audit précédent :** `2c53ef8bb5de1cc41debd7faeaabdd207fc6560d`

## 1. Résumé exécutif

Le nouveau commit améliore fortement les deux derniers constats du P2 :

* réduction de l'exposition des données lors de la génération du LDIF ;
* réconciliation des deux représentations des appartenances LDAP :

  * `member.uniqueMemberOf` ;
  * `group.uniqueMember`.

Les mots de passe, noms, adresses électroniques, dates de naissance et
descriptions ne sont plus transmis par la ligne de commande de
`generate_ldif.py`. Les mots de passe sont maintenant hachés directement
dans le générateur, supprimant l'ancien repli qui pouvait transmettre un
mot de passe en clair dans `argv`.

La synchronisation des groupes lit maintenant les deux côtés de la
relation, calcule un différentiel propre à chaque côté et permet au scan
périodique de découvrir une personne présente sur un seul des deux
côtés.

Cependant, contrairement à l'affirmation du message de commit, le P2 ne
peut pas encore être considéré comme entièrement fermé :

1. plusieurs données personnelles restent visibles dans `argv` ;
2. une variable de mot de passe absente produit silencieusement le hash d'un mot de passe vide ;
3. l'ordre « fail-closed » des écritures LDAP n'est pas réellement conditionnel ;
4. l'union des deux côtés peut restaurer une appartenance devenue obsolète ;
5. le nouveau mécanisme effectue de nombreuses recherches LDAP par membre.

Le commit annonce 999 tests réussis et une couverture de 72,10 %. Aucun
statut ni workflow GitHub Actions n'est toutefois retourné par le
connecteur pour ce SHA ; ces résultats sont donc déclarés par le commit,
mais non confirmés indépendamment.

## 2. Évaluation actualisée

| Domaine                           | Note précédente | Nouvelle note |
| --------------------------------- | --------------: | ------------: |
| Architecture applicative          |             7,7 |           7,8 |
| Qualité du code                   |             7,8 |           8,0 |
| Tests                             |             9,0 |           9,2 |
| CI et contrôles automatiques      |             9,0 |           9,0 |
| Documentation                     |             8,0 |           8,0 |
| Dépendances et reproductibilité   |             9,0 |           9,0 |
| Sécurité applicative              |             8,6 |           8,8 |
| Sécurité et fonctionnement Docker |             9,0 |           9,1 |
| Exploitation et observabilité     |             7,3 |           7,4 |

**Note globale actualisée : 8,6/10**, contre 8,5/10 précédemment.

---

# 3. Mots de passe LDIF retirés de `argv` — résolu

Les trois mots de passe sont maintenant transmis dans l'environnement
propre au processus :

```text
GENERATE_LDIF_ADMIN_PW
GENERATE_LDIF_U1_PW
GENERATE_LDIF_U2_PW
```

Les emplacements correspondants dans `GENERATE_LDIF_ARGS` contiennent
uniquement `"-"`.

Le générateur :

1. lit la variable avec `os.environ.pop()` ;
2. la retire immédiatement de son environnement ;
3. génère lui-même le hash `{SSHA}` ;
4. n'écrit jamais le mot de passe clair dans le LDIF.

L'ancien mécanisme utilisant `slappasswd` et son repli en clair a
disparu de `init.sh`. Les tests vérifient également l'absence des mots
de passe dans le résultat et la suppression des variables après lecture.

**Statut concernant les mots de passe : résolu.**

---

# 4. Principales informations personnelles retirées de `argv` — largement résolu

Les quatorze emplacements suivants utilisent désormais l'environnement :

* trois mots de passe ;
* adresse électronique de l'administrateur ;
* prénom, nom, adresse électronique, date de naissance et description de
  chaque utilisateur initial.

Le script passe quatorze tirets dans le tableau d'arguments et définit
les variables correspondantes uniquement pour l'invocation de Python.

Le générateur lit et retire ces variables avec une fonction commune.

Les tests vérifient :

* l'utilisation des valeurs de l'environnement ;
* leur absence du LDIF lorsqu'elles sont facultatives et non renseignées ;
* leur suppression de l'environnement ;
* l'absence des variables correspondantes dans le tableau Bash ;
* l'absence de l'ancien commentaire incorrect sur des arguments séparés par NUL.

## Réserve : toutes les données personnelles n'ont pas quitté `argv`

Le tableau Bash transmet encore directement :

* `ADMIN_LOGIN` ;
* `ADMIN_PSEUDONYM` ;
* les UUID des utilisateurs ;
* leurs rôles ;
* leurs pseudonymes ;
* leurs langues ;
* leurs nationalités ;
* leurs deuxième et troisième langues.

Au minimum, les pseudonymes, identifiants, rôles et nationalités sont
des données personnelles. La nationalité peut même constituer une
information particulièrement sensible selon le contexte de traitement.

L'affirmation « aucune donnée personnelle ne passe dans `argv` » est
donc trop large.

**Statut global du transport des données personnelles : partiellement
résolu.**

### Correction recommandée

Supprimer complètement l'interface positionnelle pour les données
utilisateur et transmettre une structure unique :

* JSON par l'entrée standard ;
* ou fichier temporaire `0600` ;
* ou descripteur de fichier anonyme.

La ligne de commande ne devrait plus contenir que :

```text
generate_ldif.py --input-fd 0
```

---

# 5. Variable de mot de passe manquante — nouveau risque

La fonction utilisée pour les emplacements environnementaux retourne une
chaîne vide lorsque la variable attendue est absente :

```python
return os.environ.pop(env_name, "")
```

Le mot de passe vide est ensuite accepté par `_ensure_ssha()` et
transformé en un hash `{SSHA}` valide.

Une mauvaise invocation peut donc créer silencieusement un compte dont
le mot de passe est vide.

`init.sh` fournit bien les trois variables dans le chemin normal, mais
le générateur reste utilisable directement et ne distingue pas :

* les champs obligatoires ;
* les champs facultatifs.

Les tests ne couvrent l'absence de variable que pour les dates de
naissance et descriptions, pas pour les mots de passe.

### Correction recommandée

```python
def required_slot_from_env(value, env_name):
    if value != "-":
        raise ValueError(f"{env_name} must use the environment slot")
    result = os.environ.pop(env_name, None)
    if not result:
        raise ValueError(f"{env_name} is required")
    return result
```

**Sévérité : élevée en cas d'utilisation incorrecte du générateur.**

---

# 6. Réconciliation des deux côtés LDAP — amélioration importante

`sync_member_groups()` lit maintenant séparément :

* les groupes déclarés dans `uniqueMemberOf` du membre ;
* les groupes dont `uniqueMember` contient le DN du membre.

Une divergence est journalisée avant réparation.

Le code calcule ensuite quatre différentiels :

```text
group_add
group_del
member_add
member_del
```

Chaque côté converge donc séparément vers la cible, contrairement à
l'ancien code qui calculait un seul différentiel depuis le membre.

Les tests démontrent notamment :

* la réparation d'une appartenance présente uniquement sur le membre ;
* la réparation d'une appartenance présente uniquement sur le groupe ;
* la détection d'un membre qui n'existe que du côté `uniqueMemberOf` ;
* l'ordre attendu des ajouts et suppressions.

**Statut : amélioration substantielle.**

---

# 7. L'ordre « fail-closed » n'est pas réellement appliqué

Le code appelle `_checked_modify()` dans l'ordre suivant :

* ajout : groupe, puis membre ;
* retrait : membre, puis groupe.

Cet ordre est pertinent, car l'application lit le côté membre.

Cependant, la valeur booléenne retournée par `_checked_modify()` est
ignorée.

## Exemple lors d'un ajout

1. l'ajout sur le groupe échoue ;
2. `_checked_modify()` retourne `False` ;
3. le code poursuit malgré tout ;
4. l'ajout sur le membre réussit ;
5. l'application voit immédiatement l'autorisation.

Le comportement n'est donc pas réellement « fail-closed ».

## Exemple lors d'un retrait

1. le retrait sur le membre échoue ;
2. le code retire quand même le membre du groupe ;
3. l'application continue de voir l'appartenance sur le membre.

### Correction recommandée

Pour chaque groupe, la deuxième écriture ne doit être exécutée que si la
première réussit :

```python
if _checked_modify(group_dn, group_change, operation):
    _checked_modify(member_dn, member_change, operation)
```

Pour une révocation, arrêter également le traitement du groupe lorsque
la suppression côté membre échoue.

**Statut de la gestion des échecs : partiellement résolu.**

---

# 8. L'union des deux côtés peut restaurer un état obsolète

Le calcul utilise actuellement :

```python
current = member_side | group_side
```

Cette union est transmise à la table de vérité.

Cela fonctionne bien pour réparer certaines appartenances calculées à
partir des attributs du membre. En revanche, plusieurs états persistants
sont eux-mêmes déduits des groupes existants :

* sanction ;
* conseil d'administration ;
* conseil de médiation ;
* groupes suspendus correspondants.

## Exemple : retrait du conseil d'administration

1. la suppression côté membre réussit ;
2. la suppression côté groupe échoue ;
3. au prochain scan, l'union contient toujours `boardMembersGroup` ;
4. la table de vérité considère que la personne possède encore ce rôle ;
5. le groupe est réajouté côté membre.

La divergence est « réparée », mais dans le mauvais sens.

Le même problème peut apparaître lors de la levée d'une sanction lorsque
l'un des deux côtés reste en retard.

### Correction recommandée

Définir une source autoritative pour les états persistants.

Puisque l'application lit `uniqueMemberOf`, une approche cohérente
serait :

* utiliser le côté membre comme état autoritatif ;
* écrire les ajouts côté groupe avant le membre ;
* écrire les suppressions côté membre avant le groupe ;
* ne jamais poursuivre vers le côté autoritatif si la première écriture d'un ajout échoue ;
* utiliser le scan pour faire converger le côté groupe vers le membre.

Une autre solution consiste à stocker les rôles et sanctions dans des
attributs LDAP dédiés, puis à considérer les groupes comme une vue
dérivée.

**Statut : risque de cohérence encore ouvert.**

---

# 9. Scan quotidien : couverture améliorée, coût accru

Le scan quotidien découvre désormais les membres depuis :

* les `uniqueMember` des groupes ;
* les `uniqueMemberOf` des entrées membres.

Cela corrige le cas où une personne n'était enregistrée que sur son
propre objet LDAP.

Cependant, pour chaque membre, `sync_member_groups()` interroge
individuellement chacun des groupes gérés. Avec douze groupes, le coût
devient approximativement :

```text
nombre de membres × nombre de groupes
```

auxquels s'ajoutent les recherches sur le membre et les modifications.

Sur un annuaire important, le scan peut générer plusieurs milliers ou
millions de recherches LDAP.

### Correction recommandée

Lors du scan périodique :

1. charger chaque groupe une seule fois ;
2. construire une table inverse `membre → groupes` ;
3. charger les membres en une seule recherche paginée ;
4. transmettre l'état déjà calculé à la fonction de synchronisation ;
5. ne réinterroger LDAP que lorsqu'une écriture échoue.

**Sévérité : moyenne, principalement opérationnelle.**

---

# 10. Résultats de tests

Le commit déclare :

* dix nouveaux tests ;
* 999 tests réussis ;
* une couverture de 72,10 % ;
* onze échecs observés sur l'état précédent du dépôt.

Les nouveaux tests couvrent efficacement les chemins nominaux et les
divergences déjà enregistrées. Ils ne couvrent toutefois pas encore :

* l'échec de la première écriture d'un ajout ;
* l'échec de la première écriture d'une révocation ;
* la levée de sanction avec un seul côté restant ;
* le retrait d'un rôle Board/MAC avec un seul côté restant ;
* une variable de mot de passe absente ;
* la présence des nationalités et pseudonymes dans `argv` ;
* les performances du scan sur un grand annuaire.

---

# 11. Constats antérieurs toujours ouverts

## Transport LDAP

Les connexions LDAPS valident maintenant les certificats, mais la pile
Compose utilise toujours par défaut :

```text
LDAP_PORT=389
LDAP_USE_SSL=false
```

Le transport chiffré n'est donc pas encore activé dans le déploiement
fourni.

## Tâches périodiques

Les rappels restent déclenchés depuis `NewRequest`, ce qui ne garantit
ni leur exécution sans trafic ni leur unicité en environnement
multiprocessus.

## `.env.example`

Le fichier reste incohérent avec les noms réellement utilisés :

* `MAIL_USE_TLS` au lieu de `MAIL_TLS` ;
* `MAIL_USE_SSL` au lieu de `MAIL_SSL` ;
* documentation LDAP obsolète ;
* absence de `LDAP_CA_CERT_FILE`.

## Image

Restent également ouverts :

* installation éditable de l'application ;
* paquets APT non figés ;
* absence d'obligation `--only-binary=:all:` ;
* quelques artefacts de développement encore copiés.

## Dette qualité

* mypy non bloquant ;
* Ruff limité à Pyflakes ;
* `F841` ignorée ;
* seuil de couverture à 68 % ;
* renouvellement Certbot et CSP non testés.

---

# 12. Priorités révisées

## P0 — fermé

* démarrage Docker ;
* configuration Waitress ;
* routage Apache ;
* smoke test ;
* détection de secrets.

## P1 — fermé

* verrous séparés et hashés ;
* image multiétape ;
* runtime allégé ;
* images épinglées.

## P2 — presque fermé, mais pas totalement

Résolus :

* cache LDAP ;
* validation des certificats LDAPS ;
* refresh token chiffré ;
* validation Keycloak ;
* mots de passe LDIF hors `argv` ;
* détection des divergences LDAP des deux côtés.

À terminer :

1. rendre obligatoires les variables de mots de passe du générateur ;
2. retirer toutes les données personnelles restantes de `argv` ;
3. conditionner les secondes écritures au succès des premières ;
4. choisir une source autoritative pour les rôles persistants ;
5. ajouter des tests injectant de vrais échecs LDAP.

## P3 — exploitation

1. activer et tester LDAPS dans Compose ;
2. optimiser le scan des groupes ;
3. sortir les rappels du cycle HTTP ;
4. corriger `.env.example`.

## P4 — finition

1. construire une wheel applicative ;
2. figer les dépendances APT ;
3. rendre mypy progressivement bloquant ;
4. étendre Ruff ;
5. relever le seuil de couverture ;
6. tester Certbot et la CSP.

---

# 13. Conclusion

Le commit `2bc5629…` est une amélioration réelle et importante.

Il corrige notamment :

* l'exposition la plus grave des mots de passe dans les arguments de processus ;
* le hachage de repli en clair ;
* l'impossibilité de détecter un membre enregistré uniquement sur son propre côté ;
* l'utilisation d'un différentiel unique pour deux états LDAP différents.

Il ne ferme toutefois pas complètement les deux constats :

* plusieurs données personnelles restent dans `argv` ;
* la réconciliation peut encore poursuivre une écriture après un échec ;
* l'union des deux côtés peut restaurer un rôle obsolète ;
* l'absence d'un mot de passe environnemental peut créer un hash de mot de passe vide.

**Évaluation actuelle : 8,6/10.**

Une évaluation autour de **8,9/10** deviendrait justifiée après
fermeture stricte du transport LDIF, gestion conditionnelle des
écritures LDAP et définition d'une source autoritative pour les rôles
et sanctions.
