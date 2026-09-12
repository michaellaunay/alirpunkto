---
title: "AlirPunkto — audit des dépendances et plan de mise à jour"
version: "2.0"
date: "2026-09-12"
statut: "Audit documentaire complété ; exécution des mises à jour à piloter"
reference_git: "00bd677612298b44a7532f1721b2b0064b4089a1"
python_image_actuelle: "3.12 (Dockerfile Ubuntu 24.04 ; serveur non inspecté)"
python_cible_qualification: "CPython 3.14, build standard avec GIL"
---

# AlirPunkto — audit des dépendances et plan de mise à jour

**Version 2.0 — 12 septembre 2026**  
**Base examinée :** `master` à `00bd677612298b44a7532f1721b2b0064b4089a1`, commit du 1er septembre 2026, train 0112.  
**Document initial :** audit de Claude fourni sous le nom `20260912-audit-dependances-alirpunkto.md`.  
**Usage :** document de décision, de découpage des changements et de collecte des preuves. Les cases non cochées sont des actions à réaliser, pas des opérations déjà exécutées.

> **Décision recommandée : livrer d’abord WebOb 1.8.11 sous Python 3.12 ; traiter ensuite les autres dépendances par lots ; qualifier Python 3.14 sur des verrous et une image dédiés. Ne pas présenter la pile AlirPunkto comme validée sous Python 3.14 avant les tests d’installation, de démarrage, de rendu, de persistance et d’intégration.**

## Sommaire

1. Résumé exécutif, périmètre et corrections de l’audit initial.
2. Vulnérabilités et risques de chaîne de construction.
3. Inventaire des versions et décisions par dépendance.
4. Qualification de Python 3.14 et résolution des verrous.
5. Plan d’actions détaillé, commandes et critères d’acceptation.
6. Exploitation, déploiement, retour arrière et dette séparée.
7. Preuves, limites et conditions de clôture.
8. Annexes : inventaire reconstitué, outil de contrôle et sources.

## 1. Résumé exécutif

### 1.1 Niveaux de preuve

| Code | Signification | Ce que cela ne prouve pas |
|---|---|---|
| **D** | Fichier du dépôt ou journal GitHub Actions directement consulté, à la référence indiquée. | État actuel des serveurs ni résultat d’un nouveau build. |
| **P** | Publication ou métadonnées visibles sur PyPI, recoupées par une recherche ciblée. | Résolution complète, disponibilité de tous les artefacts sur la plateforme cible, absence de retrait ultérieur. |
| **G** | Release, code ou changelog officiel amont consulté. | Publication effective du même artefact dans le miroir PyPI utilisé en CI. |
| **A** | Affirmation de l’audit de Claude, conservée avec attribution. | Vérification indépendante ou nouvelle exécution. |
| **À prouver** | Test ou mesure requis dans le plan. | Ne doit jamais être converti en « vert » sans un journal attaché. |

Une version stable publiée, une borne `Requires-Python` permissive, un classifier `Python :: 3.14` et un wheel installable sont **quatre informations différentes**. Aucune ne remplace les tests AlirPunkto. Certaines pages PyPI renvoyées par la consultation web étaient anciennes : les nouvelles publications ont donc aussi été recherchées explicitement et, notamment pour `pip-api`, recoupées avec les releases amont.

### 1.2 Décisions à prendre

| Priorité | Décision | État documentaire | Condition de livraison |
|---|---|---|---|
| **P0** | WebOb `1.8.10 → 1.8.11`, seul, dans les verrous runtime/test/qualité. | Faille et correctif confirmés ; échec CI déjà constaté. | Audit de sécurité conforme à la politique d’exception ; tests de redirection et suite 3.11/3.12. |
| **P1** | Actualiser authentification, configuration et dépendances HTTP. | Cibles récentes identifiées. | Résolution hachée, tests SSO/LDAP/configuration/TLS. |
| **P1** | Actualiser le groupe de persistance Zope. | Nouvelles versions amont confirmées. | Validation sur copie cohérente de la base et répétition du retour arrière. |
| **P1** | Ajouter une qualification réelle de Python 3.14. | Pyramid, ZODB et plusieurs dépendances déclarent déjà ce support ; Deform ne le déclare pas explicitement. | Verrous spécifiques, installation et tests applicatifs dans l’image cible. |
| **P1** | Maîtriser les dépendances de build et auditer le verrou E2E. | Angles morts confirmés dans le dépôt et les journaux. | Inventaires distincts, provenance des artefacts et contrôles bloquants. |
| **P2** | Sortir de `pkg_resources` et lever durablement la contrainte setuptools. | Dépendance directe présente dans AlirPunkto, en plus des contraintes amont. | Migration applicative + compatibilité des extensions + bornes amont compatibles. |

Sources du socle : [commit étudié][repo-commit], [configuration du projet][repo-pyproject], [CI qualité][repo-quality], [CI tests][repo-tests], [image Pyramid][repo-docker].

### 1.3 Chiffres : ne pas reconduire des totaux sans les recalculer

L’audit initial annonce **105 noms distincts, 74 à jour et 31 en retard**. Ses tableaux de retards contiennent bien **31 candidats distincts**, dont **3 non retenus en mise à jour directe** : setuptools 84, mypy 2 et pyee 14. Cela donne **au maximum 28 montées candidates**, dont WebOb ; **27 après le correctif WebOb**, avant validation du résolveur. Ce ne sont donc pas « 30 paquets à mettre à jour » dans le second commit.

Le relevé reconstitué en annexe contient **106 noms distincts** à rapprocher du total 105 annoncé par Claude. Il n’est pas une exportation automatique des quatre fichiers : le script fourni doit produire le décompte de référence au lot L0. Ne pas publier de nouveau total « à jour/en retard » tant que cette différence et les réponses PyPI n’ont pas été réconciliées.

De même, les **1 086 tests** et **environ 130 erreurs mypy** cités par Claude sont des repères historiques, pas des résultats obtenus pendant cette revue. La résolution annoncée « saine » n’a pas été réexécutée ici, et ne vaut pas preuve pour Python 3.14.

### 1.4 Corrections majeures apportées au document de Claude

| Formulation ou omission initiale | Correction dans cette version |
|---|---|
| « Le prochain run sera rouge. » | Le run `quality` du **1er septembre 2026** est déjà en échec ; son étape pip-audit identifie WebOb 1.8.10 et CVE-2026-54770. |
| Une seule date pour la faille WebOb. | Distinguer la sortie **1.8.11 du 2 août 2026**, le constat CI du 1er septembre, et la publication de l’entrée **PYSEC du 10 septembre**. |
| « Tout le reste est du rattrapage de routine. » | SSO, persistance, dépendances de build, bibliothèques anciennes et nouvelle version Python nécessitent des preuves séparées. |
| « Toute la pile déclare ≥3.10. » | Inexact comme description globale : AlirPunkto déclare `>=3.11` ; les métadonnées des bibliothèques diffèrent ; Deform ne fournit pas de `python_requires` dans le `setup.py` 3.0.1 examiné. |
| Ajouter seulement Python 3.13 en informatif. | Qualifier explicitement **3.14**. 3.13 peut servir au diagnostic, sans être une étape de production imposée. |
| Blocage setuptools attribué uniquement à Pyramid/Deform. | AlirPunkto et un test importent aussi `pkg_resources`. Il faut traiter les trois niveaux. |
| Vérification de trois verrous dans la CI sécurité. | Ajouter `requirements-e2e.lock`, puis les nouveaux verrous et la chaîne de build. |
| Pygments classé uniquement « test ». | Il est également présent dans le verrou qualité ; contrôler l’intersection des environnements. |
| Ouverture de `root()` suffisante pour Data.fs. | Les objets persistants sont chargés à la demande : l’ouverture seule ne valide ni tous les objets, ni les écritures, ni le retour arrière. |
| Installation du verrou test puis invocation de Ruff/Bandit/mypy. | Utiliser un environnement qualité séparé : ces outils ne sont pas fournis par le seul extra testing. |
| Les correctifs apt imposent toujours un nouveau digest de base. | Le digest de base **et** le contenu des couches apt/snapshots doivent être maîtrisés ; une reconstruction non mise en cache peut actualiser apt sans changer le digest. |
| Les vieilles bibliothèques sont nécessairement abandonnées ou cassées. | Ancienneté de publication = dette à évaluer ; ce n’est pas une preuve d’abandon ni d’incompatibilité. |

## 2. Vulnérabilités et chaîne de construction

### 2.1 WebOb — P0, correctif indépendant

**Installé :** `1.8.10`. **Cible :** `1.8.11`.  
**Identifiants recoupés :** `CVE-2026-54770`, `GHSA-6hx8-3wjj-gr8g`, `PYSEC-2026-3943`.  
**Source :** [avis amont][webob-advisory], [entrée PyPA][webob-pysec], [historique WebOb][webob].

Le problème concerne la normalisation de `Location` et l’interprétation différente des espaces/caractères de contrôle entre les vérifications et la résolution d’URL. La correction utilise `webob.util.urljoin` et réunit le traitement des exceptions de redirection et des réponses. L’API publique n’est pas annoncée comme modifiée, mais **le comportement de certaines URL change intentionnellement** : il faut tester les redirections normales et malformées, pas seulement l’import du paquet.

Le correctif applicatif antérieur sur `next` reste utile. Il ne remplace pas la correction de WebOb ; inversement, WebOb ne remplace pas une politique applicative d’autorisation des destinations SSO.

**Preuve CI consultée :** [run 33500131165, job 99831303271][ci-security-job], du 1er septembre 2026. Bandit passe ; l’étape pip-audit échoue avec WebOb 1.8.10, CVE-2026-54770, correctif 1.8.11. Le journal mentionne aussi des entrées ignorées : un nouveau rapport brut devra dédupliquer les alias avant d’établir un total de vulnérabilités.

**Tests d’acceptation :** chemin relatif interne ; URL absolue légitime autorisée ; `//host` ; espaces/caractères de contrôle ; URL encodées ; redirection sous reverse proxy HTTPS ; parcours login/logout/SSO. Aucun domaine réel malveillant n’est nécessaire : utiliser les domaines de test réservés.

### 2.2 setuptools — exception temporaire, pas exemption permanente

**Installé :** `80.10.2`. **Correctif annoncé :** `83.0.0`. **Version récente identifiée :** `84.0.0`.  
**Avis :** `PYSEC-2026-3447` / `CVE-2026-59890` / `GHSA-h35f-9h28-mq5c`. [Source OSV][setuptools-advisory].

L’avis concerne des exclusions de fichiers dans des distributions source et la normalisation Unicode sur macOS. Le chemin d’attaque n’est donc pas identique à celui d’un serveur HTTP Linux exécutant l’application. Il faut néanmoins examiner les machines de fabrication et les contenus publiés, pas conclure simplement « hors runtime, donc sans risque ».

| Chaîne | Contrainte ou usage observé | Conséquence |
|---|---|---|
| Deform 3.0.1 | `setuptools<81.0.0` dans son `setup.py`. | Empêche 83/84 dans le graphe runtime actuel. |
| Pyramid 2.1 | `setuptools<82`. | Une future correction de Deform seule ne suffira pas forcément. |
| AlirPunkto | `from pkg_resources import resource_filename` dans `alirpunkto/__init__.py`. | Migration applicative nécessaire pour sortir de cette API. |
| Tests AlirPunkto | Même import dans `tests/test_mandatory_fields_indicator.py`. | Adapter également la suite. |
| Build AlirPunkto | `setuptools>=68` et `wheel`, sans versions exactes. | Environnement de construction distinct, non borné comme le runtime. |

Sources : [Deform 3.0.1 — setup.py][deform-setup], [Pyramid — changements][pyramid-changes], [initialisation AlirPunkto][repo-init], [pyproject][repo-pyproject].

**Ne pas forcer setuptools 84 avec `--no-deps` pour contourner ces contraintes.** Une installation qui viole les métadonnées et casse `pkg_resources` n’est pas une remédiation acceptable. **Ce blocage de mise à jour ne démontre pas, à lui seul, une incompatibilité de setuptools 80.10.2 avec Python 3.14** : les deux sujets doivent être testés séparément.

Politique d’exception proposée, à approuver explicitement :

| Champ | Valeur proposée |
|---|---|
| Identifiant | `DEP-SEC-002` |
| Portée | Versions et environnements réellement affectés, inventoriés ; pas toutes les vulnérabilités setuptools. |
| Responsable | Mainteneur sécurité à nommer avant fusion. |
| Mesures compensatoires | Construction contrôlée, pas de sdist fabriquée sur macOS à partir d’un répertoire contenant des secrets ; inspection des archives ; environnements de build distincts. |
| Réévaluation | **Au plus tard le 12 octobre 2026**, et à chaque évolution pertinente des contraintes amont. |
| Expiration | Pas de reconduction tacite ; conserver la décision et sa justification. |
| Preuve | Rapport non filtré + rapport avec exception + versions du backend réellement utilisé. |

### 2.3 Dépendances de construction : l’angle mort des verrous hachés

Dans le job CI examiné, l’installation des sdist `pyramid-chameleon`, `pyramid-handlers` et `validate-email` déclenche explicitement l’installation de dépendances de build. L’image Pyramid autorise précisément ces trois sdist, et exige des wheels pour les autres dépendances. [Dockerfile][repo-docker] ; [journal CI][ci-security-job].

**`pip install -e . --no-deps` ne veut pas dire « aucun téléchargement »** : `--no-deps` concerne les dépendances d’installation, pas la désactivation de l’isolation de build. Un verrou runtime avec hashes ne couvre donc pas automatiquement le backend, `wheel`, les dépendances dynamiques de construction ni la version de pip.

À traiter dans le lot L4 : inventorier séparément bootstrap/résolution, build applicatif, build des trois dépendances source et runtime ; verrouiller les outils ; archiver les wheels fabriqués et leurs hashes ; installer l’application finale sans résolution implicite. Les hashes des wheels construits localement ne sont pas ceux des archives source et doivent avoir une provenance distincte.

### 2.4 Autres surfaces à ajouter à l’audit

| Surface | Contrôle nécessaire | Ne pas confondre avec… |
|---|---|---|
| `requirements-e2e.lock` | Audit Python, dépendances du pilote Playwright. | Audit des navigateurs téléchargés par Playwright. |
| Extra `dev` | Inventorier et verrouiller `pyramid_debugtoolbar` et sa chaîne si cet extra est utilisé. | Les extras testing/quality déjà verrouillés. |
| Ubuntu et apt | Scanner l’image finale ; relever digest, snapshot, versions de paquets et date de construction. | Audit des seuls paquets PyPI. |
| Actions GitHub | Vérifier SHA → version officielle, runtime Node, permissions et politique des runners. | Le seul fait d’être épinglé par SHA. |
| JS/CSS embarqués | Inventorier les versions réellement servies par Deform et l’application ; examiner leurs avis et licences. | Une absence d’alerte de pip-audit. |
| Keycloak/LDAP/SMTP/reverse proxy | Relever les versions serveur et tester les contrats d’intégration. | La version de la bibliothèque cliente Python. |
| Licences et provenance | SBOM des artefacts livrés, licences, origines et exceptions documentées. | L’autorisation automatique de toute licence vue dans les métadonnées. |

Le journal CI du 1er septembre signale en outre que les actions checkout/setup-python ciblant Node 20 sont exécutées par le runner avec Node 24. Ce signal justifie une revue dédiée des actions ; il ne démontre pas que ces étapes ont échoué — elles sont vertes dans ce job.

## 3. Inventaire des versions et décisions

### 3.1 Règles de sélection

**Épinglé** signifie la version observée dans le dépôt étudié, pas nécessairement celle des serveurs. **Cible** signifie version candidate documentée au 12 septembre, pas version déjà installée ou validée.

Les tableaux reprennent les 31 candidats de Claude en ajoutant des sources amont et des décisions. Les versions indiquées `P` sont visibles dans des pages ou historiques PyPI consultés ; `G` signifie publication/changelog officiel recoupé. La disponibilité exacte sur l’index utilisé, l’état non retiré des fichiers, `Requires-Python` et les contraintes transitives seront figés par le rapport JSON du lot L0 et par le résolveur.

On ne déduit pas le risque d’un simple nombre de version : les projets n’appliquent pas tous SemVer ; `packaging`, notamment, utilise une numérotation calendaire.

### 3.2 Runtime — R, T, Q

| Paquet | Épinglé | Cible récente | Preuve | Décision / contrôle principal |
|---|---:|---:|---|---|
| **WebOb** | 1.8.10 | **1.8.11** | P/G — [source][webob] | **L1, P0**. Séparer du reste. |
| cryptography | 50.0.0 | 50.0.1 | P — [source][p-cryptography] | L2. Chiffrement/déchiffrement, tokens conservés, wheels/ABI/OpenSSL. |
| PyJWT | 2.13.0 | **2.14.0** | P — [source][p-pyjwt] | L2. Publication du 11 septembre ; contrôle des claims, algorithmes et limites des tokens. |
| jwcrypto | 1.5.8 | **1.6.0** | P — [source][p-jwcrypto] | L2. Lire aussi les changements intermédiaires 1.5.9 ; clés/JWK/SSO. |
| python-dotenv | 1.2.2 | 1.2.3 | P — [source][p-dotenv] | L2. Rejouer le scénario 0080 avec wheel non éditable et `.env` externe. |
| zope.interface | 8.5 | 8.6 | P/G — [source][p-interface] | L3. Interfaces, adaptation, extensions natives. |
| zope.proxy | 7.2 | 7.3 | P/G — [source][p-proxy] | L3. Proxies et interactions avec objets persistants. |
| persistent | 6.7 | 6.8 | P/G — [source][p-persistent] | L3. Lecture/écriture, invalidation du cache, sérialisation. |
| BTrees | 6.4 | **6.5** | G — [source][btrees-changes] | L3. Index, invariants, conflits et persistance. |
| zodbpickle | 4.4 | **4.5** | G — [source][zodbpickle-changes] | L3. Changelog 4.5 du 20 août ; tests de données et de retour arrière. |
| anyio | 4.14.2 | 4.15.1 | P — [source][p-anyio] | L2. Appels HTTP sync/async utilisés, timeouts, fermeture des ressources. |
| charset-normalizer | 3.4.9 | 3.5.1 | P — [source][p-charset] | L2. Décodage des réponses et contenus non ASCII. |
| idna | 3.18 | 3.19 | P — [source][p-idna] | L2. Noms de domaine et URLs internationalisés. |
| packaging | 26.2 | 26.3 | P — [source][p-packaging] | L2/L4. Cohérence entre runtime et outils ; ne pas extrapoler SemVer. |
| cffi | 2.1.0 | 2.1.1 | P — [source][p-cffi] | L2. Artefacts natifs de l’architecture cible. |
| **setuptools** | 80.10.2 | 84.0.0 | P/G — [source][p-setuptools] | **Ne pas forcer.** Exception §2.2 et sortie de `pkg_resources`. |

Les sorties Zope du 20 août ne signifient pas que les versions précédentes étaient toutes incompatibles avec 3.14. Par exemple, `zodbpickle` déclare ce support dès **4.3**, `zope.proxy` dès **7.1**, `zope.interface` dès **8.1**, et `BTrees` dès **6.2**. Plusieurs nouvelles sorties préparent surtout Python 3.15. La mise à jour de maintenance et la migration de l’interpréteur sont donc deux décisions distinctes. [Changelogs Zope][zodbpickle-changes] ; [BTrees][btrees-changes] ; [zope.proxy][p-proxy] ; [zope.interface][p-interface].

### 3.3 Tests et qualité

| Paquet | Verrou concerné | Épinglé | Cible | Preuve | Décision |
|---|---|---:|---:|---|---|
| coverage | T | 7.15.2 | 7.16.0 | P — [source][p-coverage] | L4. Mesurer le delta ; conserver le seuil de 68 %. |
| Pygments | T **et Q** | 2.20.0 | 2.21.0 | P — [source][p-pygments] | L4. Vérifier la cohérence des versions communes. |
| soupsieve | T | 2.9.1 | 2.9.2 | P — [source][p-soupsieve] | L4. Sélecteurs HTML des tests fonctionnels. |
| **mypy** | Q | 1.20.2 | 2.3.1 | P — [source][p-mypy] | **Ne pas franchir `<2` dans le train de maintenance.** Analyse séparée des diagnostics et options. |
| ruff | Q | 0.16.1 | 0.16.7 | P — [source][p-ruff] | L4. Commande et règles exactement identiques à la CI. |
| cyclonedx-python-lib | Q | 11.11.0 | 11.12.0 | P — [source][p-cyclonedx] | L4. Vérifier les sorties JSON/SBOM du scanner. |
| librt | Q | 0.13.0 | 0.15.0 | P — [source][p-librt] | L4. N’accepter que la version satisfaisant le mypy conservé ; wheel cible. |
| filelock | Q | 3.32.2 | 3.32.6 | P — [source][p-filelock] | L4. Outillage ; installation propre. |
| platformdirs | Q | 4.11.0 | 4.11.8 | P — [source][p-platformdirs] | L4. Emplacements de caches et droits. |
| msgpack | Q | 1.2.1 | 1.2.2 | P — [source][p-msgpack] | L4. Extension native, cache et scanner. |
| stevedore | Q | 5.9.0 | 5.9.1 | G — [source][stevedore-release] | L4. Chargement des plugins Bandit. |
| pip-api | Q | 0.0.34 | **0.0.35** | G — [source][pip-api-release] | Release officielle du **8 septembre** ; vérifier également l’index de résolution. |
| pip | Q | 26.2 | 26.2.1 | P — [source][p-pip] | L4. Épingler aussi le bootstrap ; tester le couple pip/pip-tools. |

La borne `mypy<2` interdit mypy 2, **mais ne garantit pas que mypy restera exactement en 1.20.2** s’il existe une autre version 1.x compatible. Lors d’une mise à jour globale, utiliser une contrainte exacte temporaire pour conserver le socle voulu, ou accepter explicitement et tester un changement 1.x. Même raisonnement pour les autres dépendances transitives.

### 3.4 E2E

| Paquet | Épinglé | Version récente | Preuve | Décision |
|---|---:|---:|---|---|
| playwright | 1.62.0 | 1.62.0 observée | P — [source][p-playwright] | Conserver ; ne pas oublier les navigateurs et bibliothèques système associés. |
| pyee | 13.0.1 | 14.0.0 | P — [source][p-pyee] | Ne pas forcer. Le `pyproject.toml` du tag Playwright **v1.62.0** confirme `pyee>=13,<14` ; contrôler aussi les métadonnées de la wheel résolue. [Source][playwright-project]. |
| greenlet | 3.5.4 | 3.5.5 | P — [source][p-greenlet] | Mise à jour conditionnée à la contrainte Playwright et au wheel cible. |
| typing-extensions | 4.16.0 | Pas de changement retenu | D | Commun avec d’autres verrous ; ne pas créer de divergence non justifiée. |

Le même tag Playwright déclare **Python 3.14**, `requires-python = ">=3.10"` et `greenlet>=3.1.1,<4.0.0` : la cible greenlet 3.5.5 respecte cette borne, sans que cela valide son exécution dans AlirPunkto. [Métadonnées amont][playwright-project].

`pyee` 14 annonce en outre **Python >=3.12**. La possibilité d’utiliser un Python récent ne suffit donc pas à justifier cette montée : la dépendance consommatrice reste la première contrainte à respecter. [PyPI pyee 14][p-pyee].

### 3.5 Dépendances directes : ne pas se limiter aux paquets « en retard »

Les versions ci-dessous sont celles des verrous étudiés. « Conserver » signifie **pas de montée retenue pour ce train**, non « dernière version universellement certifiée ». Les contrôles du lot L0 doivent interroger aussi ces noms, et pas seulement les 31 lignes précédentes. [Déclarations du projet][repo-pyproject].

| Dépendance directe | Borne du projet | Version observée | Contrôle principal |
|---|---|---:|---|
| plaster_pastedeploy | `>=1.0.1,<2` | 1.0.1 | Chargement des fichiers INI et points d’entrée `pserve`. |
| pyramid | `>=2.1,<3` | 2.1 | Support 3.14 explicite en amont ; reste à intégrer dans AlirPunkto. |
| pyramid_chameleon | `>=0.3,<0.4` | 0.3 | Construction depuis sdist ; rendu de tous les templates. |
| waitress | `>=3.0.2,<4` | 3.0.2 | Démarrage, reverse proxy, headers, arrêt propre et concurrence. |
| pyramid_retry | `>=2.1.1,<3` | 2.1.1 | Rejeu des transactions sans double effet externe. |
| pyramid_tm | `>=2.6,<3` | 2.6 | Commit/abort ; intégration des erreurs et envois de messages. |
| pyramid_zodbconn | `>=0.8.1,<0.9` | 0.8.1 | Ouverture/fermeture des connexions par requête. |
| transaction | `>=5.1,<6` | 5.1 | Commits, aborts, retries et ressources participantes. |
| ZODB | `>=6.3,<7` | 6.3 | Support 3.14 annoncé depuis 6.2 ; données à qualifier. |
| pytz | `>=2024.1` | 2026.3.post1 | Dates persistées, fuseaux, transitions heure d’été/hiver. |
| **deform** | `>=3.0.1,<4` | **3.0.1** | Rendu/validation/JS/CSRF ; support 3.14 non déclaré explicitement. |
| pyramid_handlers | `>=0.5,<0.6` | 0.5 | Routes, scanning, vues et permissions ; sdist ancienne. |
| python-dotenv | `>=1.2.2,<2` | 1.2.2 | Scénario 0080 et priorité des variables déjà définies. |
| ldap3 | `>=2.9.1,<3` | 2.9.1 | Bind, TLS, recherche, création/modification et annuaire réel de test. |
| pyramid_beaker | `>=0.9,<0.10` | 0.9 | Sessions/caches ; types d’objets sérialisés réellement utilisés. |
| pyramid_mailer | `>=0.15.1,<0.16` | 0.15.1 | Envoi transactionnel, SMTP/TLS et encodage. |
| py3dns | `>=4.0.2,<5` | 4.0.2 | Résolution DNS, erreurs, IPv4/IPv6 et délais. |
| PyJWT | `>=2.7.0,<3` | 2.13.0 | Vérifications cryptographiques et claims. |
| validate_email | `>=1.3,<2` | 1.3 | Syntaxe, DNS et éventuelle vérification SMTP ; dette distincte. |
| python-keycloak | `>=7.1.1,<8` | 7.1.1 | Classifier 3.14 présent ; compatibilité serveur à vérifier séparément. |
| cryptography | `>=50.0.0,<51` | 50.0.0 | ABI, OpenSSL et compatibilité des données chiffrées. |
| bcrypt | `>=5.0.0,<6` | 5.0.0 | Authentification, erreurs et limites des mots de passe. |
| requests | `>=2.33.1,<3` | 2.34.2 | TLS, proxy, délais, redirections et décodage. |

**Sources de compatibilité déjà positives :** [Pyramid][pyramid-changes], [ZODB 6.3][p-zodb], [python-keycloak 7.1.1][p-keycloak]. Les autres extensions ne deviennent pas automatiquement qualifiées parce que Pyramid l’est.

### 3.6 Deform : résultat de la vérification demandée

Le paquet concerné est **`deform`**, et non un paquet distinct nommé `dform`.

**Dernière release officielle trouvée : Deform 3.0.1, publiée le 26 février 2026**, déjà installée dans AlirPunkto. La release 3.0.0 et son évolution vers Bootstrap 5 sont antérieures à l’état du dépôt : il ne faut pas présenter une migration Deform 2 → 3 comme une nouveauté à réaliser maintenant. [Releases officielles][deform-releases] ; [PyPI][p-deform].

Le `setup.py` du tag 3.0.1 contient la borne setuptools `<81` ; les classifiers Python vont jusqu’à **3.13** et n’incluent pas **3.14**. Cela signifie **support 3.14 non attesté dans ces métadonnées**, pas incompatibilité démontrée. La décision est de conserver 3.0.1, de surveiller une vraie publication plus récente et de faire passer les tests de formulaire sous 3.14. [Code publié][deform-setup].

Le périmètre à tester comprend aussi **Chameleon 4.6.0, Colander 2.0, Peppercorn 0.6, translationstring, iso8601**, les templates surchargés et les ressources JS/CSS effectivement utilisées. Pour Chameleon, la compilation des templates est un contrôle indispensable ; un simple `import chameleon` ne couvre pas son générateur de code. [Chameleon][p-chameleon].

## 4. Python 3.14 : qualification, pas présomption

### 4.1 Interpréteur cible et périmètre

**Cible de départ proposée : CPython 3.14.7 standard, avec GIL**, version de maintenance publiée le 5 août 2026 et vérifiée sur Python.org. Rechercher une éventuelle maintenance 3.14.x plus récente au moment du gel de la branche, puis enregistrer l’exacte version choisie et la provenance de l’image. Cette revue n’affirme pas que 3.14.7 restera la dernière lors de l’exécution. [Publication officielle][python-release].

**Hors périmètre :** `3.14t` free-threaded, JIT expérimental, Python 3.15, changement de distribution Linux simultané non qualifié. Un wheel `cp314t` ne prouve pas la compatibilité d’un wheel `cp314`, et réciproquement.

Conserver le minimum applicatif `requires-python = ">=3.11"` tant que le support de 3.11 est maintenu. Ajouter 3.14 à la CI ne justifie pas de relever automatiquement ce minimum, ni les cibles syntaxiques Ruff/mypy.

### 4.2 Matrice de preuves et travaux

| Composant | Preuve amont disponible | Point restant pour AlirPunkto | Verdict avant exécution |
|---|---|---|---|
| Pyramid 2.1 | Support Python 3.14 explicite. | App factory, configuration, routes, permissions et plugins. | Favorable, intégration à prouver. |
| WebOb 1.8.11 | Correctif de sécurité ; dépendance `legacy-cgi` pour les Python récents. | Nouveau graphe haché, POST/multipart et redirections. | Favorable sous condition de verrou adapté. |
| **Deform 3.0.1** | Métadonnées allant jusqu’à 3.13. | Rendu complet, validation, CSRF, JS et surcharge des templates. | **À qualifier explicitement.** |
| Chameleon / Colander / Peppercorn | Publications et code disponibles ; pas de preuve applicative 3.14 acquise ici. | Compilation/rendering/round-trip de formulaires. | À qualifier. |
| ZODB 6.3 | Support 3.14 depuis 6.2. | Classes persistées, historique, transactions, restauration. | Favorable, données à qualifier. |
| persistent / BTrees / zodbpickle / zope.* | Support 3.14 déjà présent dans plusieurs versions verrouillées ; nouvelles sorties documentées. | Wheels exacts + lecture/écriture/conflits et charge. | À prouver dans l’image cible. |
| python-keycloak 7.1.1 | `Requires-Python >=3.10,<4`, classifier 3.14. | Contrat avec le serveur, refresh, logout, état/nonce selon le flux utilisé. | Favorable, intégration à prouver. |
| cryptography / bcrypt / cffi | Wheels natifs ou ABI stable selon le paquet et la plateforme. | Sélection du wheel correct, OpenSSL, chiffrement, authentification. | Vérification artefact + tests requise. |
| ldap3 / py3dns | Pas de preuve applicative complète établie ici. | SSL/TLS, bind, DNS, délais, erreurs et serveur de test. | À qualifier, pas remplacement d’office. |
| pyramid_handlers / mailer / beaker / zodbconn | Extensions anciennes présentes. | Build, imports et scénarios intégrés respectifs. | À qualifier ; dette séparée si besoin. |
| setuptools 80.10.2 | Contraintes amont identifiées. | Installation et usage de `pkg_resources` sous 3.14. | Ne pas confondre dette sécurité et incompatibilité Python. |
| pytest / coverage / outils | Versions candidates et, pour certains, artefacts 3.14 visibles. | Installation sous le Python de leur job et comparaison des résultats. | À prouver par environnement. |
| Playwright / greenlet | Playwright 1.62.0 déclare 3.14 ; greenlet est borné `>=3.1.1,<4.0.0`. Paquets et navigateur distincts. | Pilote, navigateur, dépendances OS, parcours du serveur 3.14. | À qualifier séparément. |

### 4.3 Dépendance conditionnelle réellement pertinente : `legacy-cgi`

`cgi` n’est plus dans la bibliothèque standard depuis Python 3.13. Le `setup.py` de **WebOb 1.8.11** confirme exactement `legacy-cgi>=2.6; python_version>='3.13'`. Cette dépendance ne doit pas être ajoutée artificiellement au graphe 3.12, mais résolue et hachée pour 3.14. [Métadonnées du tag][webob-setup]. Un verrou calculé sous **3.12** peut donc être complet pour 3.12 mais **incomplet pour 3.14**, même si les versions de WebOb et de l’application restent identiques. [Historique WebOb][webob] ; [legacy-cgi][p-legacy-cgi].

Le graphe 3.14 doit inclure cette dépendance, sa version, ses hashes et son audit si le marqueur de la version WebOb retenue l’exige. **Ne pas contourner un échec de `--require-hashes` en désactivant les hashes ou les dépendances.** Faire recalculer le graphe avec le bon interpréteur.

### 4.4 Changements Python à rechercher dans le code réellement exécuté

Ces points sont des **axes d’inspection**, pas une liste de bogues déjà trouvés dans AlirPunkto. La référence est la [documentation de migration Python 3.14][python-whatsnew], complétée par celle de 3.13 pour les retraits intermédiaires.

| Zone | Recherche / test à prévoir |
|---|---|
| Annotations différées | Code d’introspection et bibliothèques qui inspectent directement les annotations. |
| API retirées de `pkgutil` / `importlib` | Usages de `find_loader`, `get_loader`, anciennes interfaces de ressources ; tester les points d’entrée et les templates. |
| AST et génération de code | Compiler et rendre les templates Chameleon, ne pas se limiter aux imports. |
| asyncio | Appels à `get_event_loop()` sans boucle courante ; parcours HTTP asynchrones réellement utilisés. |
| Multiprocessing et sérialisation | Méthode de démarrage, objets picklés, importabilité des fonctions ; seulement si ces fonctions sont utilisées. |
| TLS et dépendances crypto | Version OpenSSL du Python, bibliothèques embarquées dans les wheels, certificats, erreurs TLS. |
| Ressources de paquet | Remplacement de `pkg_resources` en respectant la durée de vie des fichiers obtenus par `importlib.resources.as_file`. |
| Avertissements | Relever les nouveaux avertissements ; rendre bloquants ceux du code applicatif après tri, sans masquer en bloc ceux des dépendances. |

### 4.5 Stratégie de verrous et de CI

Les quatre verrous actuels sont générés avec Python **3.12**. La documentation pip-tools recommande de compiler dans l’environnement correspondant à la cible, car les marqueurs d’environnement interviennent dans la résolution. [pip-tools][pip-tools].

Organisation proposée, sans déplacer les chemins consommés par la production actuelle :

```text
requirements.lock                      # runtime 3.12, chemin actuel conservé
requirements-test.lock                 # tests du socle actuel
requirements-quality.lock              # outillage actuel
requirements-e2e.lock                  # pilote E2E actuel
requirements/py314/runtime.lock         # nouveaux fichiers de qualification
requirements/py314/test.lock
requirements/py314/quality.lock
requirements/py314/e2e.lock
requirements-build.in                  # à créer : besoin de build explicitement recensé
requirements-build.lock                # à produire et auditer
```

La compatibilité des verrous actuels avec le job Python 3.11 doit aussi rester vérifiée. Si des marqueurs rendent un seul jeu 3.12 impropre à 3.11, générer un jeu 3.11 dédié plutôt que modifier à la main les dépendances conditionnelles.

| Job | Statut au début | Condition avant bascule de l’application |
|---|---|---|
| Tests 3.11 / 3.12 | Bloquants, comme aujourd’hui. | Restent verts jusqu’à décision explicite de retrait de support. |
| Tests 3.14 + installation complète | Informatif sur branche de qualification. | **Devient bloquant avant déclaration de support/livraison 3.14.** |
| Image applicative 3.14 + smoke / données | Nouveau job. | **Bloquant** avant bascule. |
| Qualité 3.12 | Bloquant sauf mypy informatif. | Conserver les contrôles de sécurité et lint. |
| Outils qualité 3.14 | Qualification additionnelle. | Un outil peut rester isolé sous 3.12 si ce choix est documenté ; ne pas annoncer alors « tous les outils validés en 3.14 ». |
| Pilote E2E | Peut rester sous 3.12. | Doit tester **le serveur 3.14** et les parcours définis ; le Python du pilote n’est pas celui du serveur. |
| Python 3.13 | Diagnostic facultatif. | Utile pour localiser un retrait d’API, pas passage en production obligatoire. |

### 4.6 Wheels, architecture et image

Valider dans l’OS et l’architecture destinés à la production, au minimum `linux/amd64` si c’est la plateforme déployée ; ajouter `linux/arm64` uniquement si elle est réellement supportée. Relever `sys.version`, `platform`, `SOABI`, les tags de wheels et OpenSSL. Les wheels `abi3` peuvent être compatibles sans porter littéralement `cp314` : utiliser les tags acceptés par pip, pas une recherche de sous-chaîne dans le nom.

L’image existante installe `python3` depuis Ubuntu 24.04 et fabrique une venv 3.12. **Modifier seulement la matrice GitHub Actions n’en fait pas une image 3.14.** Créer une recette dédiée fournissant réellement 3.14, épinglée par digest vérifié, puis reconstruire la venv dans cette image. Ne pas copier une venv 3.12 dans un runtime 3.14. Maintenir les mêmes chemins de configuration, UID, volumes, certificats, healthcheck et paramètres réseau, ou traiter chaque différence explicitement. [Dockerfile étudié][repo-docker].

## 5. Plan d’actions détaillé

### 5.1 Tableau de pilotage

Le numéro 0113 est conservé pour le **correctif urgent**. Les lots suivants constituent des PR/commits séparables ; leur numéro de train définitif doit respecter le carnet du dépôt. Aucun ticket n’est déclaré terminé dans ce document.

| ID | Lot / résultat attendu | Priorité | Dépend de | Responsable proposé | État / preuve |
|---|---|---|---|---|---|
| DEP-000 | Figer SHA, sources, inventaires, baseline et compte des paquets. | P0 | — | Mainteneur | À faire ; rapport L0. |
| DEP-001 | WebOb 1.8.11, seul, trois verrous. | P0 | DEP-000 | Développeur + relecteur | À faire ; diff sémantique + CI. |
| DEP-002 | Exception setuptools datée, limitée et approuvée. | P1 | DEP-000 | Référent sécurité | À faire ; décision signée. |
| DEP-003 | Lot auth/config/HTTP/crypto. | P1 | DEP-001 | Développeur | À faire ; tests ciblés + suite. |
| DEP-004 | Lot Zope/persistance. | P1 | DEP-001 | Développeur + exploitant | À faire ; rapport données. |
| DEP-005 | Outils test/qualité/E2E et audit des quatre verrous. | P1 | DEP-001 | Mainteneur CI | À faire ; rapports par verrou. |
| DEP-006 | Verrouiller et documenter la chaîne de build. | P1 | DEP-000 | Mainteneur CI | À faire ; wheels + provenance. |
| DEP-007 | Retirer les usages applicatifs de `pkg_resources`. | P2 | DEP-000 | Développeur | À faire ; tests ressources. |
| DEP-008 | Produire les quatre graphes Python 3.14. | P1 | DEP-003/004/005 | Mainteneur CI | À faire ; résolution/installation. |
| DEP-009 | Qualifier Deform et toutes les extensions sous 3.14. | P1 | DEP-008 | Développeur | À faire ; matrice de scénarios. |
| DEP-010 | Construire et tester l’image applicative 3.14. | P1 | DEP-006/008/009 | Exploitant | À faire ; digest + smoke + charge. |
| DEP-011 | Revue images apt/snapshots, actions et actifs navigateur. | P1/P2 | DEP-000 | Exploitant + CI | À faire ; inventaires hors PyPI. |
| DEP-012 | Répéter sauvegarde, déploiement et retour arrière. | P1 | Lot effectivement déployé | Exploitant | À faire ; procès-verbal. |
| DEP-013 | Recette, décision GO/NO-GO et documentation FR/EN. | P1 | Preuves du lot | Responsable projet | À faire ; validation explicite. |

Un lot n’attend pas nécessairement tous les autres : **DEP-001 doit pouvoir être livré seul**. Les dépendances indiquées pour Python 3.14 décrivent le chemin recommandé après mise à jour du socle, sans obliger à fusionner tous les changements dans un unique commit.

### 5.2 Lot L0 — préparation, inventaire et baseline

**Objectif :** disposer d’un état de départ reproductible et d’un inventaire sourcé avant toute réécriture de verrou.

```bash
set -euo pipefail
BASE=00bd677612298b44a7532f1721b2b0064b4089a1
git clone https://github.com/michaellaunay/alirpunkto.git alirpunkto-deps
cd alirpunkto-deps
git switch -c audit/dependencies-20260912 "$BASE"
git config pull.ff only
mkdir -p evidence/20260912/before
for f in requirements.lock requirements-test.lock requirements-quality.lock requirements-e2e.lock; do
    cp "$f" "evidence/20260912/before/$f"
done
git rev-parse HEAD > evidence/20260912/base-sha.txt
sha256sum requirements*.lock > evidence/20260912/before/locks.sha256
python3.12 -m venv .venv-lock-312
.venv-lock-312/bin/python -m pip install 'pip==26.2.1' 'pip-tools==7.6.0'
.venv-lock-312/bin/python -m pip --version
.venv-lock-312/bin/python -m piptools compile --version
```

Les versions de bootstrap ci-dessus sont des **candidates documentées, à qualifier ensemble**. Ce premier amorçage doit être tracé ; il ne remplace pas le verrou de build complet du lot L4. Ne pas installer cet outillage dans la venv de production.

Copier le script `audit_pypi.py` fourni avec ce document à l’endroit choisi pour les outils d’audit, puis lancer depuis la racine :

```bash
.venv-lock-312/bin/python audit_pypi.py \
    --repo . --inventory-only \
    --output evidence/20260912/inventory-before

.venv-lock-312/bin/python audit_pypi.py \
    --repo . --as-of 2026-09-12 --python 3.14.7 \
    --output evidence/20260912/pypi-before
```

Le script conserve les noms normalisés, les versions par verrou, les réponses PyPI, leurs dates de collecte et leurs hashes. Il écarte les préversions et les fichiers retirés visibles, mais **ne résout pas les contraintes transitives et ne teste pas les wheels**. Une erreur réseau ne doit pas être comptée comme « paquet à jour ».

Actions complémentaires : relever les versions exactes des interpréteurs, outils, images et serveurs de test ; confirmer l’architecture cible ; récupérer le dernier résultat des suites ; recalculer le nombre de paquets ; capturer un audit brut sans exception et un audit avec la politique approuvée ; lire les changelogs entre version installée et version candidate, pas uniquement la dernière entrée.

**Acceptation L0 :** inventaire sans ligne en erreur, totaux réconciliés, SHA fixé, conditions de résolution enregistrées, responsables nommés et preuve de sauvegarde des verrous. Les sorties peuvent rester locales si elles contiennent des chemins sensibles ; les secrets, tokens, `.env` et données personnelles ne doivent pas entrer dans les preuves publiées.

### 5.3 Lot L1 — commit WebOb seul, train 0113

Conserver le même Python et la même version de pip-tools pour les trois compilations. **Aucun `--upgrade` global.**

```bash
set -euo pipefail
COMPILE=.venv-lock-312/bin/pip-compile
COMMON=(--allow-unsafe --generate-hashes --strip-extras \
        --upgrade-package 'webob==1.8.11')
"$COMPILE" "${COMMON[@]}" -o requirements.lock pyproject.toml
"$COMPILE" "${COMMON[@]}" --extra testing -o requirements-test.lock pyproject.toml
"$COMPILE" "${COMMON[@]}" --extra quality -o requirements-quality.lock pyproject.toml
git diff -- requirements.lock requirements-test.lock requirements-quality.lock
```

**Contrôle du diff :** une seule version de paquet doit changer : WebOb. Ne pas imposer arbitrairement « exactement deux hashes modifiés » : le nombre d’artefacts/hashes et les commentaires peuvent évoluer. Toute autre version changée doit être expliquée ou retirée du correctif isolé.

**Preuve rouge/vert :** archiver le rapport de l’ancien verrou et celui du nouveau sous le même scanner et la même politique. La preuve rouge historique existe déjà en CI ; refaire un comparatif actuel évite de confondre disparition de l’alerte WebOb et évolution de la base d’avis. Le résultat attendu n’est pas « zéro vulnérabilité absolue », mais « aucune vulnérabilité non acceptée ; WebOb corrigé ».

Exécuter les tests de redirection du §2.1, puis les suites et le smoke 3.12. Ne pas ajouter de nouvelles dérogations pip-audit pour faire passer le commit.

**Message de commit proposé :**

```text
fix(deps): upgrade WebOb to 1.8.11 for Location-header redirect safety

Fix CVE-2026-54770 in the runtime, testing and quality locks without
upgrading unrelated packages. Preserve application redirect validation.

Proof: <CI run, audit reports and redirect regression tests actually run>.
Refs: PYSEC-2026-3943, GHSA-6hx8-3wjj-gr8g
```

Remplacer le champ `Proof` par les résultats obtenus ; ne pas committer une affirmation de réussite copiée de cet exemple.

### 5.4 Lot L2 — authentification, configuration, HTTP et crypto

Candidats : `cryptography`, `cffi`, `PyJWT`, `jwcrypto`, `python-dotenv`, `anyio`, `charset-normalizer`, `idna`, `packaging`.

Méthode recommandée : libérer explicitement ces paquets avec des `--upgrade-package 'nom==version'` répétés, dans R/T/Q, à partir des fichiers issus de L1. Examiner les dépendances ajoutées, supprimées ou contraintes différemment. Ne pas résoudre chaque environnement à des dates différentes sans contrôler leurs intersections.

| Scénario | Résultat attendu |
|---|---|
| Login et synchronisation LDAP | Succès/échec corrects ; `givenName` et `sn` ne régressent pas ; absence d’attribut traitée comme dans le train 0112. |
| SSO et JWT | Algorithmes autorisés explicitement ; signature, expiration et claims requis contrôlés ; rejet des tokens invalides. |
| Refresh et chiffrement | Tokens déjà scellés relus ; nouveaux tokens relus après redémarrage ; rotation de clés selon le fonctionnement existant. |
| Protection des tailles | Scénarios sur données incompressibles et tokens surdimensionnés conservés. |
| `.env` | Lancement depuis le répertoire réel du conteneur ; wheel non éditable ; priorité de l’environnement et secret absent géré correctement. |
| HTTP/TLS/DNS | Timeouts, erreurs, certificat invalide, encodage, proxy et fermeture des connexions vérifiés. |

Commande de sélection initiale, **à compléter par la liste effective des tests collectés** :

```bash
.venv-test-312/bin/python -m pytest tests -k 'sso or keycloak or token'
```

Cette sélection n’est pas une preuve de couverture de tout le lot. Ajouter les tests de configuration, LDAP, authentification locale et réseau qui existent dans le dépôt ; créer les cas manquants identifiés. Un test intégralement mocké n’atteste pas la compatibilité du serveur Keycloak ou de slapd.

**Acceptation L2 :** résolution et installation propres dans R/T/Q, `pip check` sans erreur, tests ciblés et suite complète verts, aucune régression des secrets/tokens ni changement implicite de stratégie d’authentification.

### 5.5 Lot L3 — Zope, ZODB et données

Candidats : `zope.interface`, `zope.proxy`, `persistent`, `BTrees`, `zodbpickle`. Conserver ZODB/ZEO/transaction aux versions retenues tant qu’aucune résolution ou anomalie ne justifie leur évolution.

**Avant les tests :** obtenir une copie cohérente et autorisée de la base, des éventuels blobs et de la configuration nécessaire. Les sauvegardes ZODB peuvent contenir des données personnelles et des secrets ; elles restent dans un environnement de confiance. Une base pickle non fiable peut exécuter du code lors de son chargement : ne pas utiliser de fichier non maîtrisé.

Protocole minimal de qualification :

1. Vérifier la sauvegarde, son empreinte, son origine et la cohérence Data.fs/blobs. Une copie brute pendant des écritures n’est pas une procédure de sauvegarde universelle.
2. Dans l’environnement candidat, ouvrir la copie en **lecture seule**. Un simple `root()` constitue uniquement un smoke test.
3. Forcer le chargement des objets applicatifs et références persistantes pertinents ; vérifier les classes, champs, index BTrees et compteurs métier. Documenter le périmètre réellement parcouru et les éventuels objets non accessibles depuis les racines choisies.
4. Examiner aussi l’historique si l’exploitation exige sa lecture/restauration ; ne pas assimiler « objets vivants lisibles » à « toutes les révisions vérifiées ».
5. Sur une seconde copie jetable, créer/modifier/supprimer les objets autorisés, committer, annuler, provoquer un conflit/retry, fermer puis rouvrir. Vérifier l’absence de doublon de mail ou de modification LDAP lors d’un retry.
6. Répéter avec l’ancien environnement sur une copie des données ayant subi les écritures de test, afin de qualifier le retour arrière ; sinon classer la restauration de sauvegarde comme obligatoire.
7. Tester la procédure d’upgrade uniquement après avoir inspecté ses effets. Ne pas assimiler `tools/run_upgrades.py --dry-run` à une garantie de lecture seule sans vérifier son implémentation et les migrations concernées.

**À proscrire dans ce lot :** pack/compactage, purge, renommage de classes persistées, changement simultané du schéma et de l’interpréteur sans procédure dédiée. Ne pas « réparer » une base pendant un test censé seulement vérifier sa compatibilité.

**Acceptation L3 :** rapport de lecture/écriture/retry/restauration avec versions, hashes, nombres d’objets vérifiés, anomalies et résultat de réouverture. Échec de chargement d’une classe, divergence d’index ou incertitude sur le retour arrière = **NO-GO** pour le lot concerné.

### 5.6 Lot L4 — outils, sécurité et fabrication

**Environnements séparés :** `.venv-lock-312`, `.venv-test-312`, `.venv-quality-312` et `.venv-e2e-312`. Ne pas additionner les extras dans une même venv comme unique preuve : cela peut masquer une dépendance manquante dans le verrou runtime.

Préparation des environnements de contrôle, à refaire de zéro dans le clone de qualification :

```bash
set -euo pipefail
python3.12 -m venv .venv-test-312
python3.12 -m venv .venv-quality-312
.venv-test-312/bin/python -m pip install --require-hashes -r requirements-test.lock
.venv-quality-312/bin/python -m pip install --require-hashes -r requirements-quality.lock
.venv-test-312/bin/python -m pip install -e . --no-deps
.venv-quality-312/bin/python -m pip install -e . --no-deps
.venv-test-312/bin/python -m pip check
.venv-quality-312/bin/python -m pip check
```

Ces commandes reproduisent le mode editable de la CI actuelle et **laissent son défaut d’isolation de build visible**. Le contrôle du paquet final est distinct : construire une wheel de l’application dans l’environnement de build maîtrisé, puis l’installer sans dépendances dans une venv runtime propre ; tester aussi cette installation non éditable. Une fois le verrou de build produit, utiliser une procédure contrôlée sans téléchargements implicites plutôt que conserver ce défaut.

Commandes qualité à garder alignées avec la CI :

```bash
.venv-quality-312/bin/ruff check \
    alirpunkto tests tools docker/apply_server_overrides.py docker/generate_ldif.py
.venv-quality-312/bin/bandit -r alirpunkto tools -ll -q
.venv-quality-312/bin/mypy alirpunkto
```

mypy reste informatif dans la politique actuelle. Capturer sa sortie complète et son code de retour dans une étape dédiée ; ne pas la masquer avec un pipeline `tail -1` dépourvu de `pipefail`. Relever les diagnostics nouveaux plutôt qu’un seul total, et distinguer changement de version de l’outil et évolution du code.

Audit avec l’exception setuptools **uniquement après approbation et contrôle de sa date** :

```bash
set -euo pipefail
mkdir -p evidence/20260912/security
failed=0
for lock in requirements.lock requirements-test.lock requirements-quality.lock requirements-e2e.lock; do
    name="$(basename "$lock" .lock)"
    if .venv-quality-312/bin/pip-audit --no-deps \
        --ignore-vuln PYSEC-2026-3447 \
        --format json -r "$lock" \
        > "evidence/20260912/security/${name}.json" \
        2> "evidence/20260912/security/${name}.stderr"; then
        printf '%s\n' 0 > "evidence/20260912/security/${name}.exit-code"
    else
        rc=$?
        printf '%s\n' "$rc" > "evidence/20260912/security/${name}.exit-code"
        failed=1
    fi
done
exit "$failed"
```

Une erreur réseau ou un rapport invalide est un échec de vérification, pas une absence de faille. Archiver également les rapports **sans** l’option d’exception, dans un répertoire distinct, sans écraser les précédents. Étendre la boucle aux verrous de build et aux jeux 3.14 lorsqu’ils existent. La politique doit vérifier la date d’expiration avant d’autoriser l’ignore.

**Build reproductible :** relever les dépendances PEP 517 déclarées et dynamiques ; construire les trois sdist autorisées et l’application dans des environnements propres ; archiver leur provenance, les outils utilisés et les wheels résultants ; scanner l’image finale. Ne pas prétendre à une reproductibilité bit à bit avant de l’avoir mesurée.

**Acceptation L4 :** quatre verrous audités, outils disponibles dans le bon job, cohérence des pins partagés, seuil de couverture inchangé, pas de nouvelle exception silencieuse, fabrication documentée.

**Marqueurs et audit de sécurité :** auditer un verrou 3.14 avec un scanner exécuté dans l’environnement 3.14 correspondant, ou un inventaire/SBOM complètement résolu pour cette cible. Un scanner exécuté sous 3.12 peut écarter des lignes conditionnelles destinées à 3.14. Le mode `--no-deps` ne vérifie pas la complétude du graphe ; conserver également `pip check` et le rapport de l’installation cible.

### 5.7 Lot L5 — `pkg_resources` et qualification Python 3.14

**Ressources applicatives.** Remplacer `resource_filename` par les interfaces appropriées d’`importlib.resources` sans supposer qu’un `Traversable` est toujours un chemin de fichier permanent. Pour une ressource extraite avec `as_file`, conserver le contexte aussi longtemps que son chemin est utilisé. Tester le chargement des templates, traductions et fichiers statiques depuis la wheel installée. Ne pas considérer la disparition de l’import applicatif comme la levée automatique des contraintes de Deform et Pyramid.

**Compilation des graphes 3.14**, avec l’interpréteur réellement installé sur la machine de qualification :

```bash
set -euo pipefail
python3.14 -m venv .venv-lock-314
.venv-lock-314/bin/python -m pip install 'pip==26.2.1' 'pip-tools==7.6.0'
.venv-lock-314/bin/python -VV
mkdir -p requirements/py314
C=.venv-lock-314/bin/pip-compile
"$C" --allow-unsafe --generate-hashes --strip-extras \
    -o requirements/py314/runtime.lock pyproject.toml
"$C" --allow-unsafe --generate-hashes --strip-extras --extra testing \
    -o requirements/py314/test.lock pyproject.toml
"$C" --allow-unsafe --generate-hashes --strip-extras --extra quality \
    -o requirements/py314/quality.lock pyproject.toml
"$C" --allow-unsafe --generate-hashes --strip-extras \
    -o requirements/py314/e2e.lock requirements-e2e.in
```

Les fichiers de sortie étant nouveaux, cette commande peut sélectionner des versions plus récentes que le socle 3.12. **Examiner le diff des noms/versions et ne pas fusionner aveuglément.** Pour isoler l’effet de Python, construire d’abord un candidat avec des contraintes sur les pins communs du socle accepté, puis libérer seulement les conflits justifiés. Les nouveaux paquets conditionnels doivent être résolus normalement. Conserver la provenance des contraintes ; ne jamais recopier simplement le verrou 3.12 en le renommant « py314 ».

Installer chaque graphe dans une venv 3.14 vide, exécuter `pip check` et enregistrer le rapport d’installation. Pour le runtime, appliquer la même politique wheels/sdist que l’image actuelle :

```bash
python3.14 -m venv .venv-runtime-314
.venv-runtime-314/bin/python -m pip install \
    --require-hashes --only-binary=:all: \
    --no-binary=pyramid-chameleon,pyramid-handlers,validate-email \
    --report evidence/20260912/install-runtime-314.json \
    -r requirements/py314/runtime.lock
.venv-runtime-314/bin/python -m pip check
```

Cette vérification doit être répétée dans l’image cible et avec la chaîne de construction maîtrisée du lot L4. Le succès d’une venv hôte ne suffit pas si l’image possède une autre libc, un autre OpenSSL ou une autre architecture. Toute compilation native supplémentaire inattendue doit être expliquée ; ne pas ajouter silencieusement un compilateur pour masquer l’absence de wheel.

**Tests bloquants de l’application 3.14 :**

| ID | Famille de tests | Critère |
|---|---|---|
| PY314-01 | Installation runtime seule + wheel applicative | Aucun paquet implicite manquant, `pip check` sans erreur, points d’entrée fonctionnels. |
| PY314-02 | Création de l’application, INI et `.env` | Démarrage non éditable identique à la configuration cible. |
| PY314-03 | Formulaires Deform | GET, POST valide/invalide, CSRF, champs obligatoires, erreurs, i18n et widgets réellement employés. |
| PY314-04 | Templates / actifs | Compilation complète, ressources présentes, JS sans erreur bloquante, CSP conforme. |
| PY314-05 | LDAP/SSO/crypto/mails | Scénarios du lot L2 avec services de test et effets externes maîtrisés. |
| PY314-06 | Données et transactions | Protocole L3 sous 3.14, puis répétition du retour arrière. |
| PY314-07 | Suite et couverture | Tests complets sans échec nouveau ; seuil 68 % maintenu ; comparaison des mesures documentée. |
| PY314-08 | Image / réseau / charge | Smoke, reverse proxy, concurrence, arrêt/redémarrage, mémoire et temps de réponse dans les budgets approuvés. |

### 5.8 Lot L6 — suite complète et revue de livraison

Reprendre les variables d’environnement de `.github/workflows/tests.yml` avec des secrets de **test** générés, un annuaire de test et aucun accès aux services de production. Ne pas réutiliser la vraie `.env` pour rendre la suite verte.

```bash
.venv-test-312/bin/python -m pytest -p no:cacheprovider -q \
    --junitxml=evidence/20260912/pytest-312.xml \
    --cov=alirpunkto --cov-fail-under=68
```

Répéter avec l’environnement 3.11, puis 3.14 dédié lorsque ce lot est prêt. Ajouter un rapport de couverture exploitable si nécessaire, sans retirer le seuil. Mesurer la baseline et le candidat avec la **même version** de coverage pour distinguer une baisse réelle d’un changement de mesure. Une variation n’autorise ni baisse automatique du seuil, ni dissimulation de code devenu non testé.

Rejouer la pile de test décrite dans `docker/test-docker-compose.yaml` et les scénarios des workflows smoke/E2E effectivement présents. Le présent document ne prétend pas avoir exécuté ces workflows ni disposer des données de production.

**Séparation recommandée des commits :** correctif WebOb ; lot auth/config ; lot persistance ; outils/CI ; chaîne de build ; ressources applicatives ; qualification 3.14 ; image et recette. Garder les messages Conventional Commits en anglais et le corps `Problem / Fix / Proof` selon l’usage du projet. Ne pas annoncer un nombre de tests fixe dans un modèle de commit avant exécution.

## 6. Exploitation, déploiement et dette séparée

### 6.1 Images de base et paquets système

Le Dockerfile Pyramid consulté utilise `ubuntu:24.04` au digest `sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90` et prévoit un paramètre `UBUNTU_SNAPSHOT`. L’audit de Claude indique un même épinglage dans quatre Dockerfiles : le lot exploitation doit vérifier chacun d’eux plutôt que recopier cette affirmation. [Dockerfile][repo-docker].

Le digest rend la **base** immuable ; il ne verrouille pas automatiquement les paquets récupérés dans une couche `apt-get update/install`. À l’inverse, un cache Docker réutilisé ou un snapshot apt inchangé peut maintenir des paquets anciens. La procédure doit donc enregistrer **digest de base + snapshot éventuel + date/paramètres du build + inventaire apt de l’image finale**, puis scanner les quatre images réellement déployées.

Examiner `openssl`, certificats CA, slapd, postfix, apache2, certbot et les autres paquets présents, sans supposer leurs versions à partir du seul nom Ubuntu. La migration du Python applicatif ne met pas à jour ces composants par elle-même.

### 6.2 Actions GitHub et automatisation

Activer ou ajuster une surveillance distincte pour `github-actions`, Python et images Docker selon les fichiers réellement suivis. Examiner chaque proposition : version publiée, SHA complet, changement de runtime Node, permissions minimales, comportement sur contributions externes et exigences du runner. Aucun nouveau SHA n’est inventé dans ce document.

Conserver les mises à jour de workflows séparées du correctif WebOb lorsque possible. Examiner également les étapes de téléchargement des navigateurs Playwright et les caches : le scanner des paquets Python ne couvre pas tous leurs composants.

### 6.3 Environnements de déploiement — faits rapportés, à confirmer

L’audit de Claude décrit **kuneagi02** comme instance neuve et **kuneagi01** comme production historique, épinglée à `e6603d22`, en attente de validation client. Ces informations proviennent du document fourni, pas d’une inspection des serveurs pendant cette revue.

**Conserver la consigne : ne pas modifier kuneagi01 dans ce train.** Toute migration de cette instance reste soumise à la validation client et au dossier de migration existant, à relire dans son intégralité avant intervention. Un test sur une copie de kuneagi02 ne prouve pas la compatibilité des données plus anciennes de kuneagi01.

Pour kuneagi02 ou une préproduction équivalente, déployer un **artefact identifié par digest** issu du commit validé. Éviter `git pull && docker compose build` comme unique mécanisme de livraison : cette commande ne garantit ni la référence déployée, ni le contenu des dépendances téléchargées pendant le build.

### 6.4 Séquence de déploiement autorisable

| Étape | Action | Preuve attendue |
|---|---|---|
| Avant | Confirmer instance, commit, digest, verrous, interpréteur et fenêtre autorisée. | Fiche de déploiement approuvée. |
| Sauvegarde | Sauvegarder les données et systèmes impliqués selon une procédure cohérente ; tester l’accès à la restauration. | Identifiant, empreinte, date, contrôle de restauration. |
| Préproduction | Installer l’image validée ; exécuter smoke, login/SSO, modification d’un membre test et mails contrôlés. | Résultats et journaux expurgés. |
| Bascule | Appliquer la méthode approuvée, contrôler healthcheck, erreurs, latences et traitements en cours. | Horodatage et métriques. |
| Surveillance | Vérifier redirections, login, `sn`/`givenName`, sessions, transactions et queue de mails. | Comparatif à la baseline. |
| Clôture | Confirmer le lot réellement déployé et les exceptions encore ouvertes. | Signature/validation ; documentation à jour. |

### 6.5 Retour arrière : code **et** données

**Correctif WebOb seul :** disposer de l’image précédente, mais se rappeler qu’elle contient la faille. En cas de régression, privilégier le retrait de l’exposition ou un correctif testé plutôt qu’un retour prolongé à la version vulnérable.

**Lot persistance ou Python :** un retour à l’ancienne image ne suffit pas si le nouvel environnement a écrit des données que l’ancien ne sait pas traiter. La procédure doit préciser si les nouveaux fichiers sont rétrocompatibles **par test**, ou si une restauration de sauvegarde est requise. Définir la perte de données maximale acceptable et le traitement des modifications externes déjà effectuées dans LDAP, Keycloak ou SMTP.

Déclencheurs de retour arrière : erreurs de désérialisation, corruption ou divergence d’index, régression d’authentification, violations des invariants métier, duplications d’effets externes ou dépassement des budgets de disponibilité/latence approuvés. Les valeurs de ces budgets sont à fixer à partir de l’exploitation réelle, pas inventées dans l’audit.

### 6.6 Dette à planifier hors correctif urgent

| Sujet | Travail réel nécessaire | Condition de départ |
|---|---|---|
| Sortie complète de `pkg_resources` / setuptools ancien | Adapter AlirPunkto et ses tests, inspecter les plugins, vérifier les nouvelles contraintes Pyramid/Deform ; contribution ou fork éventuel gouverné. | Ticket séparé ; ne pas lever les bornes artificiellement. |
| `validate_email` 1.3 | Comparer syntaxe, normalisation, DNS et éventuel SMTP à un remplacement. `email-validator` n’est pas automatiquement un remplacement à comportement identique. | Tests de contrat existants puis migration dédiée. |
| `pyramid_handlers` 0.5 | Inventorier routes, scanning, prédicats, permissions et conventions avant internalisation ou remplacement. | Pas d’affirmation « trivial à internaliser » sans inventaire. |
| `pyramid_mailer` / `repoze.sendmail` | Garanties transactionnelles, queue, retries, encodage et TLS ; conserver les effets après commit attendus. | Tests d’intégration et procédure d’exploitation. |
| mypy 2 | Mesurer diagnostics et différences de configuration ; améliorer progressivement le socle. | Pas de seuil arbitraire « moins de 50 erreurs » comme unique critère. |
| `pytz` → `zoneinfo`, si retenu | Compatibilité des dates/fuseaux persistés et des usages applicatifs. | Pas une dépendance nécessaire du passage à Python 3.14. |
| Moteurs/actifs de formulaires | Versions JS réelles, surcharge des widgets et licences. | Ne pas confondre dette front et version Python Deform. |

## 7. Preuves, limites et clôture

### 7.1 Ce qui a effectivement été vérifié pendant cette revue

Lecture de l’audit fourni ; référence du dépôt ; configuration des dépendances et extras ; verrous et extraits pertinents ; workflows tests/qualité ; Dockerfile Pyramid ; usages applicatifs de `pkg_resources` ; releases/métadonnées/changelogs amont ; avis WebOb et setuptools ; **journal réel de l’échec pip-audit du 1er septembre**.

Les cibles de version des tableaux ont été recoupées avec des publications officielles. Pour `BTrees`, `zodbpickle`, `stevedore` et `pip-api`, la preuve de nouvelle publication présentée ici repose notamment sur le changelog ou la release amont ; leur présence exacte et leur état de retrait sur l’index de construction restent à enregistrer par le script/résolveur.

### 7.2 Ce qui n’a pas été exécuté ou certifié ici

**Pas de nouvelle résolution pip-compile, de nouveau scan pip-audit, d’installation de toute la pile sous 3.14, d’exécution de pytest AlirPunkto, de build Docker ni de lecture de Data.fs de production.** Le journal CI existant n’est pas présenté comme une exécution de la pile mise à jour.

Les digests actuels des registres, les nouvelles versions/SHA de toutes les actions, les versions apt des serveurs, la totalité des actifs JS et les configurations LDAP/Keycloak/SMTP déployées ne sont pas certifiés par cette revue. Les mentions de serveurs et de versions de production issues de Claude doivent être confirmées par l’exploitant.

La vérification web n’est pas une archive exhaustive de l’état historique de PyPI : des pages peuvent être en cache et les retraits de fichiers peuvent changer. Le lot L0 formalise la collecte de référence. L’absence d’avis connu dans un scanner ne constitue pas une preuve d’absence de vulnérabilité.

### 7.3 Dossier de preuve attendu pour chaque lot

```text
evidence/<date>/<lot>/
  base-and-candidate-sha.txt
  environment.txt                 # sans secrets
  locks.sha256
  inventory.json / inventory.csv
  raw-pypi/                       # réponses et provenance
  resolver.log
  install-report-*.json
  pip-check-*.txt
  audit-raw-*.json
  audit-policy-*.json
  security-exceptions.md
  pytest-*.xml
  coverage-*.json
  targeted-scenarios.md
  image-digest-and-sbom.txt
  data-compatibility.md            # références, pas copie de la base
  rollback-rehearsal.md
  decision.md
```

### 7.4 Checklist GO/NO-GO

- [ ] Les versions et les noms distincts ont été recalculés depuis les fichiers réels ; le désaccord 105/106 est résolu.
- [ ] Les cibles existent sur l’index utilisé, avec fichiers acceptés et hashes ; aucun retrait ou conflit n’a été ignoré.
- [ ] Les verrous d’un même environnement ont des pins partagés cohérents ; les ajouts conditionnels sont audités.
- [ ] WebOb est corrigé ; toute exception restante possède une portée, un responsable et une échéance.
- [ ] Installation propre, `pip check`, suite, scénarios ciblés et contrôle non éditable sont réussis.
- [ ] Le lot persistance possède sa preuve de lecture/écriture/restauration lorsqu’il est inclus.
- [ ] Le build et l’image livrés sont identifiés, audités et conformes à l’environnement validé.
- [ ] Le support Python 3.14 n’est déclaré qu’après passage des tests bloquants du §5.7 dans l’image cible.
- [ ] Le déploiement est autorisé pour l’instance visée ; kuneagi01 reste exclue sans validation dédiée.
- [ ] Le retour arrière a été répété et les impacts sur les données/effets externes sont maîtrisés.
- [ ] Les tickets, CHANGES.txt, l’audit français et son miroir anglais reflètent les résultats réellement obtenus.

**Règle de clôture : une case sans preuve est une case ouverte. L’audit de pilotage peut être adopté maintenant ; la mise à jour et la compatibilité Python ne sont acquises qu’après l’exécution des lots correspondants.**

## Annexe A — Inventaire reconstitué des pins

Ce relevé facilite la revue des dépendances non reprises dans les seuls tableaux de retards. Il est reconstitué depuis les fichiers et le journal d’installation consultés, **pas généré à partir d’un clone local**. Il doit être remplacé ou rapproché de l’export `audit_pypi.py --inventory-only` avant gel du train.

`R` = runtime ; `Q+` = noms supplémentaires du verrou qualité ; `T+` = noms supplémentaires de test non déjà listés ; `E+` = noms supplémentaires E2E. Cette partition compte chaque nom une fois et **ne décrit pas toutes ses occurrences** : Pygments, par exemple, est rangé dans Q+ mais apparaît aussi en test ; typing-extensions est rangé dans R mais apparaît aussi en E2E.

| Nom normalisé | Pin observé | Groupe de comptage |
|---|---:|---|
| `aiofiles` | 25.1.0 | R |
| `anyio` | 4.14.2 | R |
| `bcrypt` | 5.0.0 | R |
| `beaker` | 1.14.1 | R |
| `btrees` | 6.4 | R |
| `certifi` | 2026.7.22 | R |
| `cffi` | 2.1.0 | R |
| `chameleon` | 4.6.0 | R |
| `charset-normalizer` | 3.4.9 | R |
| `colander` | 2.0 | R |
| `cryptography` | 50.0.0 | R |
| `deform` | 3.0.1 | R |
| `deprecation` | 2.1.0 | R |
| `h11` | 0.16.0 | R |
| `httpcore` | 1.0.9 | R |
| `httpx` | 0.28.1 | R |
| `hupper` | 1.12.1 | R |
| `idna` | 3.18 | R |
| `iso8601` | 2.1.0 | R |
| `jwcrypto` | 1.5.8 | R |
| `ldap3` | 2.9.1 | R |
| `packaging` | 26.2 | R |
| `pastedeploy` | 3.1.0 | R |
| `peppercorn` | 0.6 | R |
| `persistent` | 6.7 | R |
| `plaster` | 1.1.2 | R |
| `plaster-pastedeploy` | 1.0.1 | R |
| `py3dns` | 4.0.2 | R |
| `pyasn1` | 0.6.4 | R |
| `pycparser` | 3.0 | R |
| `pyjwt` | 2.13.0 | R |
| `pyramid` | 2.1 | R |
| `pyramid-beaker` | 0.9 | R |
| `pyramid-chameleon` | 0.3 | R |
| `pyramid-handlers` | 0.5 | R |
| `pyramid-mailer` | 0.15.1 | R |
| `pyramid-retry` | 2.1.1 | R |
| `pyramid-tm` | 2.6 | R |
| `pyramid-zodbconn` | 0.8.1 | R |
| `python-dotenv` | 1.2.2 | R |
| `python-keycloak` | 7.1.1 | R |
| `pytz` | 2026.3.post1 | R |
| `repoze-sendmail` | 4.5 | R |
| `requests` | 2.34.2 | R |
| `requests-toolbelt` | 1.0.0 | R |
| `setuptools` | 80.10.2 | R |
| `transaction` | 5.1 | R |
| `translationstring` | 1.4 | R |
| `typing-extensions` | 4.16.0 | R |
| `urllib3` | 2.7.0 | R |
| `validate-email` | 1.3 | R |
| `venusian` | 3.1.1 | R |
| `waitress` | 3.0.2 | R |
| `webob` | 1.8.10 | R |
| `zc-lockfile` | 4.0 | R |
| `zconfig` | 4.3 | R |
| `zdaemon` | 5.2.1 | R |
| `zeo` | 6.2 | R |
| `zodb` | 6.3 | R |
| `zodbpickle` | 4.4 | R |
| `zodburi` | 3.0.0 | R |
| `zope-deferredimport` | 6.1.1 | R |
| `zope-deprecation` | 6.0 | R |
| `zope-interface` | 8.5 | R |
| `zope-proxy` | 7.2 | R |
| `bandit` | 1.9.4 | Q+ |
| `boolean-py` | 5.0 | Q+ |
| `cachecontrol` | 0.14.4 | Q+ |
| `cyclonedx-python-lib` | 11.11.0 | Q+ |
| `defusedxml` | 0.7.1 | Q+ |
| `filelock` | 3.32.2 | Q+ |
| `librt` | 0.13.0 | Q+ |
| `license-expression` | 30.4.4 | Q+ |
| `markdown-it-py` | 4.2.0 | Q+ |
| `mdurl` | 0.1.2 | Q+ |
| `msgpack` | 1.2.1 | Q+ |
| `mypy` | 1.20.2 | Q+ |
| `mypy-extensions` | 1.1.0 | Q+ |
| `packageurl-python` | 0.17.6 | Q+ |
| `pathspec` | 1.1.1 | Q+ |
| `pip` | 26.2 | Q+ |
| `pip-api` | 0.0.34 | Q+ |
| `pip-audit` | 2.10.1 | Q+ |
| `pip-requirements-parser` | 32.0.1 | Q+ |
| `platformdirs` | 4.11.0 | Q+ |
| `py-serializable` | 2.1.0 | Q+ |
| `pygments` | 2.20.0 | Q+ |
| `pyparsing` | 3.3.2 | Q+ |
| `pyyaml` | 6.0.3 | Q+ |
| `rich` | 15.0.0 | Q+ |
| `ruff` | 0.16.1 | Q+ |
| `sortedcontainers` | 2.4.0 | Q+ |
| `stevedore` | 5.9.0 | Q+ |
| `tomli` | 2.4.1 | Q+ |
| `tomli-w` | 1.2.0 | Q+ |
| `beautifulsoup4` | 4.15.0 | T+ |
| `coverage` | 7.15.2 | T+ |
| `iniconfig` | 2.3.0 | T+ |
| `pluggy` | 1.6.0 | T+ |
| `pytest` | 9.1.1 | T+ |
| `pytest-cov` | 7.1.0 | T+ |
| `soupsieve` | 2.9.1 | T+ |
| `webtest` | 3.0.7 | T+ |
| `greenlet` | 3.5.4 | E+ |
| `playwright` | 1.62.0 | E+ |
| `pyee` | 13.0.1 | E+ |

**Partition du relevé : R = 65 ; Q+ = 30 ; T+ = 8 ; E+ = 3 ; total = 106.** Ces nombres ne sont pas les tailles complètes des verrous Q/T/E. Sources : [runtime][repo-runtime-lock], [test][repo-test-lock], [qualité][repo-quality-lock], [E2E][repo-e2e-lock] et [journal d’installation de la CI][ci-security-job].

## Annexe B — Outil de contrôle fourni

Le script **`audit_pypi.py`** joint est un outil de collecte en lecture seule. Il lit les verrous, compare les noms normalisés et archive les métadonnées PyPI dans un dossier de sortie. Il ne modifie pas les verrous, n’installe aucun paquet et ne déclenche aucun déploiement.

| Fonction | Portée |
|---|---|
| Inventaire | Noms uniques, pins par fichier, hashes des fichiers d’entrée et détection de divergences. |
| Versions | Plus haute version stable ayant des fichiers publiés avant la fin du jour UTC demandé et non retirés au moment de la collecte. |
| Python | `Requires-Python` et classifier 3.14 de la version récente ; **pas un test d’exécution**. |
| Artefacts | Liste des noms de wheels ; **pas une validation des tags de la plateforme cible**. |
| Provenance | Réponses JSON brutes, URL, date de collecte et empreinte SHA-256. |
| Mode hors ligne | Réanalyse du cache déjà collecté ; ne prétend pas découvrir de nouvelles publications. |
| Échecs | Code 2 si collecte/format incomplet ; code 3 si pins divergents à examiner ; pas de faux résultat « tout à jour ». |

Prérequis : Python >=3.11 et le paquet `packaging`, normalement présent dans l’environnement d’outillage proposé. Les fichiers avec inclusions `-r/-c`, références VCS ou pins conditionnels multiples ne sont pas pris en charge par ce petit outil : ils sont refusés explicitement plutôt que partiellement ignorés. Les marqueurs simples sont conservés, pas évalués.

L’option `--as-of` filtre les dates de publication, **pas l’historique des retraits**. Un `Requires-Python` permissif ne tient pas compte des bornes du projet et des autres paquets : la résolution pip-tools reste obligatoire. Les fichiers de sortie ne doivent pas être présentés comme un scan de sécurité ni comme la preuve que toute l’application fonctionne sous 3.14.

**Autocontrôle réalisé sur le script fourni : 19 tests hors ligne réussis sous Python 3.13.5.** Ils couvrent le parseur, les filtres de versions et de retraits, les erreurs de collecte et les codes de sortie. Ils ne sont pas les tests AlirPunkto et ne prouvent pas la compatibilité Python 3.14. Journal : `verification-outil.txt`.

## Annexe C — Sources de référence

Les liens ci-dessous sont des sources primaires ou des fichiers du projet. Consultation documentaire : **12 septembre 2026**. Les références Git du projet sont figées ; les pages PyPI et les pages `latest` peuvent évoluer. Archiver les preuves retenues au moment de la résolution.

Les liens PyPI renvoient aux pages canoniques des projets ou des versions identifiées. La vérification documentaire a parfois utilisé l’historique ou un résultat indexé d’une autre page de version ; elle ne se substitue pas à la collecte JSON ni au contrôle des fichiers non retirés du lot L0. Les assertions sur l’application sont rattachées aux fichiers figés ci-dessous.

| Référence | Document |
|---|---|
| `repo-commit` | [Commit audité][repo-commit] |
| `repo-pyproject` | [Projet, bornes, extras et build][repo-pyproject] |
| `repo-tests` | [Workflow tests][repo-tests] |
| `repo-quality` | [Workflow qualité et audit][repo-quality] |
| `repo-docker` | [Dockerfile Pyramid][repo-docker] |
| `repo-init` | [Initialisation et import pkg_resources][repo-init] |
| `repo-runtime-lock` | [Verrou runtime][repo-runtime-lock] |
| `repo-test-lock` | [Verrou test][repo-test-lock] |
| `repo-quality-lock` | [Verrou qualité][repo-quality-lock] |
| `repo-e2e-lock` | [Verrou E2E][repo-e2e-lock] |
| `ci-security-job` | [CI sécurité du 1er septembre 2026, job 99831303271][ci-security-job] |
| `webob` | [WebOb — publications et historique][webob] |
| `webob-setup` | [WebOb 1.8.11 — dépendance conditionnelle legacy-cgi][webob-setup] |
| `webob-advisory` | [Avis WebOb GHSA-6hx8-3wjj-gr8g][webob-advisory] |
| `webob-pysec` | [Entrée PyPA PYSEC-2026-3943][webob-pysec] |
| `setuptools-advisory` | [Avis setuptools PYSEC-2026-3447, agrégation OSV][setuptools-advisory] |
| `deform-setup` | [Deform 3.0.1 — dépendances et classifiers][deform-setup] |
| `deform-releases` | [Deform — releases officielles][deform-releases] |
| `playwright-project` | [Playwright v1.62.0 — dépendances et support Python][playwright-project] |
| `pyramid-changes` | [Pyramid — changements, dont support Python 3.14][pyramid-changes] |
| `btrees-changes` | [BTrees — documentation et historique des versions][btrees-changes] |
| `zodbpickle-changes` | [zodbpickle — changelog du tag 4.5][zodbpickle-changes] |
| `stevedore-release` | [OpenStack Hibiscus — releases dont stevedore 5.9.1][stevedore-release] |
| `pip-api-release` | [pip-api 0.0.35 — release du 8 septembre 2026][pip-api-release] |
| `python-release` | [CPython 3.14.7 — publication officielle][python-release] |
| `python-whatsnew` | [Python 3.14 — nouveautés et portage][python-whatsnew] |
| `pip-tools` | [pip-tools — compilation selon environnement et mises à jour ciblées][pip-tools] |
| `p-deform` | [PyPI — deform 3.0.1][p-deform] |
| `p-zodb` | [PyPI — ZODB 6.3][p-zodb] |
| `p-keycloak` | [PyPI — python-keycloak 7.1.1][p-keycloak] |
| `p-chameleon` | [PyPI — Chameleon : historique / métadonnées][p-chameleon] |
| `p-legacy-cgi` | [PyPI — legacy-cgi : historique / métadonnées][p-legacy-cgi] |
| `p-cryptography` | [PyPI — cryptography 50.0.1][p-cryptography] |
| `p-pyjwt` | [PyPI — PyJWT 2.14.0][p-pyjwt] |
| `p-jwcrypto` | [PyPI — jwcrypto 1.6.0][p-jwcrypto] |
| `p-dotenv` | [PyPI — python-dotenv 1.2.3][p-dotenv] |
| `p-interface` | [PyPI — zope.interface 8.6][p-interface] |
| `p-proxy` | [PyPI — zope.proxy 7.3][p-proxy] |
| `p-persistent` | [PyPI — persistent 6.8][p-persistent] |
| `p-anyio` | [PyPI — anyio 4.15.1][p-anyio] |
| `p-charset` | [PyPI — charset-normalizer 3.5.1][p-charset] |
| `p-idna` | [PyPI — idna : historique / métadonnées][p-idna] |
| `p-packaging` | [PyPI — packaging : historique / métadonnées][p-packaging] |
| `p-cffi` | [PyPI — cffi : historique / métadonnées][p-cffi] |
| `p-setuptools` | [PyPI — setuptools : historique / métadonnées][p-setuptools] |
| `p-coverage` | [PyPI — coverage 7.16.0][p-coverage] |
| `p-pygments` | [PyPI — Pygments 2.21.0][p-pygments] |
| `p-soupsieve` | [PyPI — soupsieve : historique / métadonnées][p-soupsieve] |
| `p-mypy` | [PyPI — mypy : historique / métadonnées][p-mypy] |
| `p-ruff` | [PyPI — ruff 0.16.7][p-ruff] |
| `p-cyclonedx` | [PyPI — cyclonedx-python-lib 11.12.0][p-cyclonedx] |
| `p-librt` | [PyPI — librt 0.15.0][p-librt] |
| `p-filelock` | [PyPI — filelock 3.32.6][p-filelock] |
| `p-platformdirs` | [PyPI — platformdirs 4.11.8][p-platformdirs] |
| `p-msgpack` | [PyPI — msgpack 1.2.2][p-msgpack] |
| `p-pip` | [PyPI — pip : historique / métadonnées][p-pip] |
| `p-playwright` | [PyPI — playwright 1.62.0][p-playwright] |
| `p-pyee` | [PyPI — pyee 14.0.0][p-pyee] |
| `p-greenlet` | [PyPI — greenlet : historique / métadonnées][p-greenlet] |

[repo-commit]: https://github.com/michaellaunay/alirpunkto/commit/00bd677612298b44a7532f1721b2b0064b4089a1
[repo-pyproject]: https://github.com/michaellaunay/alirpunkto/blob/00bd677612298b44a7532f1721b2b0064b4089a1/pyproject.toml
[repo-tests]: https://github.com/michaellaunay/alirpunkto/blob/00bd677612298b44a7532f1721b2b0064b4089a1/.github/workflows/tests.yml
[repo-quality]: https://github.com/michaellaunay/alirpunkto/blob/00bd677612298b44a7532f1721b2b0064b4089a1/.github/workflows/quality.yml
[repo-docker]: https://github.com/michaellaunay/alirpunkto/blob/00bd677612298b44a7532f1721b2b0064b4089a1/docker/DockerfilePyramid
[repo-init]: https://github.com/michaellaunay/alirpunkto/blob/00bd677612298b44a7532f1721b2b0064b4089a1/alirpunkto/__init__.py
[repo-runtime-lock]: https://github.com/michaellaunay/alirpunkto/blob/00bd677612298b44a7532f1721b2b0064b4089a1/requirements.lock
[repo-test-lock]: https://github.com/michaellaunay/alirpunkto/blob/00bd677612298b44a7532f1721b2b0064b4089a1/requirements-test.lock
[repo-quality-lock]: https://github.com/michaellaunay/alirpunkto/blob/00bd677612298b44a7532f1721b2b0064b4089a1/requirements-quality.lock
[repo-e2e-lock]: https://github.com/michaellaunay/alirpunkto/blob/00bd677612298b44a7532f1721b2b0064b4089a1/requirements-e2e.lock
[ci-security-job]: https://github.com/michaellaunay/alirpunkto/actions/runs/33500131165/job/99831303271
[webob]: https://pypi.org/project/WebOb/
[webob-advisory]: https://github.com/Pylons/webob/security/advisories/GHSA-6hx8-3wjj-gr8g
[webob-pysec]: https://github.com/pypa/advisory-database/blob/main/vulns/webob/PYSEC-2026-3943.yaml
[setuptools-advisory]: https://osv.dev/vulnerability/PYSEC-2026-3447
[deform-setup]: https://github.com/Pylons/deform/blob/3.0.1/setup.py
[deform-releases]: https://github.com/Pylons/deform/releases
[playwright-project]: https://github.com/microsoft/playwright-python/blob/v1.62.0/pyproject.toml
[pyramid-changes]: https://docs.pylonsproject.org/projects/pyramid/en/latest/changes.html
[btrees-changes]: https://btrees.readthedocs.io/en/latest/
[zodbpickle-changes]: https://github.com/zopefoundation/zodbpickle/blob/4.5/CHANGES.rst
[stevedore-release]: https://releases.openstack.org/hibiscus/index.html
[pip-api-release]: https://github.com/di/pip-api/releases/tag/0.0.35
[python-release]: https://www.python.org/downloads/release/python-3147/
[python-whatsnew]: https://docs.python.org/3.14/whatsnew/3.14.html
[pip-tools]: https://pip-tools.readthedocs.io/en/stable/
[p-deform]: https://pypi.org/project/deform/3.0.1/
[p-zodb]: https://pypi.org/project/ZODB/6.3/
[p-keycloak]: https://pypi.org/project/python-keycloak/7.1.1/
[p-chameleon]: https://pypi.org/project/Chameleon/
[p-legacy-cgi]: https://pypi.org/project/legacy-cgi/
[p-cryptography]: https://pypi.org/project/cryptography/50.0.1/
[p-pyjwt]: https://pypi.org/project/PyJWT/2.14.0/
[p-jwcrypto]: https://pypi.org/project/jwcrypto/1.6.0/
[p-dotenv]: https://pypi.org/project/python-dotenv/1.2.3/
[p-interface]: https://pypi.org/project/zope.interface/8.6/
[p-proxy]: https://pypi.org/project/zope.proxy/7.3/
[p-persistent]: https://pypi.org/project/persistent/6.8/
[p-anyio]: https://pypi.org/project/anyio/4.15.1/
[p-charset]: https://pypi.org/project/charset-normalizer/3.5.1/
[p-idna]: https://pypi.org/project/idna/
[p-packaging]: https://pypi.org/project/packaging/
[p-cffi]: https://pypi.org/project/cffi/
[p-setuptools]: https://pypi.org/project/setuptools/
[p-coverage]: https://pypi.org/project/coverage/7.16.0/
[p-pygments]: https://pypi.org/project/Pygments/2.21.0/
[p-soupsieve]: https://pypi.org/project/soupsieve/
[p-mypy]: https://pypi.org/project/mypy/
[p-ruff]: https://pypi.org/project/ruff/0.16.7/
[p-cyclonedx]: https://pypi.org/project/cyclonedx-python-lib/11.12.0/
[p-librt]: https://pypi.org/project/librt/0.15.0/
[p-filelock]: https://pypi.org/project/filelock/3.32.6/
[p-platformdirs]: https://pypi.org/project/platformdirs/4.11.8/
[p-msgpack]: https://pypi.org/project/msgpack/1.2.2/
[p-pip]: https://pypi.org/project/pip/
[p-playwright]: https://pypi.org/project/playwright/1.62.0/
[p-pyee]: https://pypi.org/project/pyee/14.0.0/
[p-greenlet]: https://pypi.org/project/greenlet/


[webob-setup]: https://github.com/Pylons/webob/blob/1.8.11/setup.py
