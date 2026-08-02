# Audit externe du dépôt (ChatGPT), douzième passage — 2 août 2026

**Provenance.** Douzième passage de l'audit statique externe
(ChatGPT, à la demande de Michaël Launay), sur le commit `4481288a`
(trains 0079 à 0082 fusionnés) ; passage précédent sur `777074c2`.
Note globale proposée : **8,8/10** — stable au plus haut de la série,
avec un **dixième domaine inauguré : « Harnais multi-agent : 7,6 »**
qui retient la note pendant que la CI (9,0), Docker (9,1) et la
documentation (8,8) progressent. Chaîne des passages : 6,5 → 6,9 →
6,7 → 7,1 → 7,8 → 8,2 → 8,5 → 8,6 → 8,4 → 8,3 → 8,8 → 8,8.

**Statut.** Contre-expertisé le jour même. L'architecture du harnais
est validée sans réserve — `AGENTS.md` reconnu nativement par Codex
et Kimi Code CLI, import `@AGENTS.md` officiel côté Claude Code — et
les six constats de configuration sont **tous fondés**, dont un
particulièrement instructif : le motif `Read(./.env.*)` bloquait le
fichier suivi `.env.example`, reproduisant dans notre propre harnais
la classe d'erreur (motif trop large) que la série d'audits traque
partout ailleurs. Corrections livrées par le train 0083 (fusionné
`b9e8bc51`) : refus en chemins sensibles précis (`.env.example`
redevenu lisible, verrou `fnmatch`), installation des **deux**
verrous hachés dans l'environnement documenté, section « Exact CI
commands » aux commandes littérales des workflows (la CI ruff
alignée **vers le haut** sur les deux scripts docker), wording
« garde-fous » dans `CLAUDE.md`, `.gitignore` appris
`.kimi-code/local.toml`, et la suite `tests/test_agent_harness.py`
demandée au §11 (sept verrous, dont la parité
commandes↔workflow). Le `$schema` optionnel (P1.5) est resté dehors,
l'URL du schemastore n'ayant pas pu être confirmée. **Réserve
maintenue au §13** : la troisième exécution smoke (correctif Referer)
n'était confirmée ni par le connecteur de l'auditeur ni par nous à la
date du versement.

## Suites données

0083 (corrections P0+P1 du harnais, chroniquées ci-dessus) et le
chapitre [14 — Développer avec des agents IA](../architecture/14_agents_ia.md)
(installation et configuration des trois agents, exemples sur ce
dépôt). Restent au carnet : les items P2 (harnais depuis machine
vierge, découverte par les trois agents), le smoke vert observable,
et les P3 applicatifs inchangés — persistance des sanctions (décision
de design en cours), sérialiseur LDIF, scan, planificateur externe,
`.env.example`.

# Texte intégral de l'audit (douzième passage)

Audit actualisé du dépôt AlirPunkto — douzième
passage
Date : 2 août 2026
Dépôt : michaellaunay/alirpunkto
Branche : master
Commit examiné : 4481288aaedac54316d04f8e4b4f0ce8e8b2da60
Audit précédent : 777074c25f0c55c58a13cf166945cdde8dfeef77

## 1. Résumé exécutif
Quatre commits ont été ajoutés depuis le passage précédent :

    1. archivage documentaire des audits manquants ;
    2. correction de la recherche de .env depuis l’application installée en wheel ;
    3. ajout du harness multi-agent ;
    4. correction du test smoke HTTPS pour reproduire le comportement réel d’un navigateur lors du
       contrôle CSRF.

Le harness repose sur :

     • AGENTS.md comme contrat commun ;
     • CLAUDE.md comme couche Claude Code ;
     • .claude/settings.json comme politique de permissions Claude ;
     • .claude/settings.local.json exclu de Git pour les adaptations locales.

Cette architecture est pertinente :

     • Codex reconnaît officiellement AGENTS.md comme fichier d’instructions du dépôt ;
     • Kimi Code CLI charge également le fichier AGENTS.md du projet ;
     • Claude Code utilise CLAUDE.md et prend en charge l’import @AGENTS.md , exactement comme
       le fait le dépôt.

La configuration Claude est un JSON valide et utilise des champs officiellement pris en charge :

     • permissions.allow ;
     • permissions.ask ;
     • permissions.deny ;
     • permissions.defaultMode .

Toutefois, le harness n’est pas encore exempt d’erreurs :

    1. Read(./.env.*) bloque involontairement le fichier suivi .env.example ;
    2. docker/.env.test , qui contient des identifiants locaux générés, n’est pas explicitement
       interdit à Claude ;
    3. l’installation décrite dans AGENTS.md ne fournit ni Ruff ni Bandit ;
    4. les commandes qualité du harness ne correspondent pas exactement à celles de la CI ;
    5. aucune suite de tests ne verrouille encore les fichiers du harness ;

    6. les « blocages » Claude peuvent être contournés par des commandes Bash équivalentes et
       doivent donc être présentés comme des garde-fous, non comme un confinement absolu.

Le harness est donc bien conçu mais encore partiellement mal configuré.

## 2. Évaluation actualisée
               Domaine                                 Note précédente      Nouvelle note

               Architecture applicative                               8,1             8,2

               Qualité du code                                        8,4             8,5

               Tests unitaires et structurels                         9,4             9,4

               CI et tests d’intégration                              8,9             9,0

               Documentation                                          8,6             8,8

               Dépendances et reproductibilité                        9,4             9,4

               Sécurité applicative                                   9,1             9,1

               Sécurité et fonctionnement Docker                      9,0             9,1

               Exploitation et observabilité                          7,6             7,7

               Harness multi-agent                                    —               7,6

Note globale actualisée : 8,8/10.

La maturité de la pile Docker progresse, mais les erreurs de permissions Claude et de préparation de
l’environnement empêchent encore de relever la note globale.

## 3. Compatibilité Claude Code — correcte
3.1 Chargement des instructions
Le fichier CLAUDE.md commence par :

  @AGENTS.md

Il ajoute ensuite uniquement les règles spécifiques à Claude Code :

     • conversation en français ;
     • code et commits en anglais ;
     • livraison sous forme de patch numéroté ;
     • absence de git push ;
     • exécution complète des tests ;

       • respect de la politique .claude/settings.json .

Claude Code prend officiellement en charge :

       • CLAUDE.md comme mémoire de projet ;
       • les imports utilisant la syntaxe @chemin ;
       • l’utilisation de @AGENTS.md pour partager des instructions avec d’autres agents.

Statut : configuration de chargement correcte.

3.2 Taille et structure
 AGENTS.md contient environ 129 lignes et CLAUDE.md 19 lignes.

Le contenu reste organisé par rubriques :

       • environnement ;
       • commandes ;
       • livraison ;
       • règles de sécurité ;
       • pièges de tests ;
       • CI.

Cela évite un CLAUDE.md monolithique et permet de conserver un contrat commun aux trois agents.

Statut : satisfaisant.

## 4. Erreur Claude : .env.example est bloqué
La politique contient simultanément :

  "allow": [
    "Read(./**)"
  ]

et :

  "deny": [
    "Read(./.env)",
    "Read(.env)",
    "Read(./.env.*)"
  ]

Les règles de lecture Claude utilisent des motifs de type gitignore, et les refus sont évalués avant les
demandes et autorisations. Un refus correspondant ne peut donc pas être compensé par
 Read(./**) .

Le motif :

  ./.env.*

correspond notamment à :

  .env.example

Or .env.example est un fichier suivi par Git, destiné précisément à être audité et corrigé. Il contient
d’ailleurs plusieurs incohérences déjà identifiées :

      • MAIL_USE_TLS au lieu de MAIL_TLS ;
      • MAIL_USE_SSL au lieu de MAIL_SSL ;
      • exemple LDAP_SERVER ambigu ;
      • absence de LDAP_CA_CERT_FILE .

Claude Code sera donc empêché de lire un fichier qu’il devrait pouvoir examiner.

Correction recommandée
Remplacer le motif large par des chemins sensibles précis :

  "deny": [
    "Read(./.env)",
    "Read(.env)",
    "Read(./docker/.env)",
    "Read(./docker/.env.test)",
    "Read(./docker/secrets/**)",
    "Bash(git push:*)",
    "Bash(rm -rf:*)",
    "Edit(./requirements.lock)",
    "Edit(./requirements-test.lock)",
    "Edit(./requirements-quality.lock)"
  ]

Ne pas interdire :

  .env.example

Statut : erreur de configuration confirmée.

Sévérité : moyenne, car elle bloque une activité légitime plutôt qu’elle ne crée directement une fuite.

## 5. Erreur Claude : docker/.env.test reste
lisible
La politique interdit :

  "Read(./docker/.env)"

mais pas :

  docker/.env.test

Or docker/init_test.sh génère ce fichier avec notamment :

      • mot de passe LDAP local ;
      • mot de passe administrateur ;
      • mots de passe des comptes de test ;
      • clé de session ;
      • configuration complète de la pile locale.

Même s’il s’agit de valeurs locales ou de test, elles restent des identifiants qui ne devraient pas être
automatiquement intégrés au contexte d’un agent.

Le fichier est correctement ignoré par Git, mais l’exclusion Git ne constitue pas une restriction de lecture
pour Claude Code.

Correction nécessaire
Ajouter :

  "Read(./docker/.env.test)"

à permissions.deny .

On peut également protéger les variantes futures de manière explicite :

  "Read(./docker/.env.local)"
  "Read(./docker/.env.production)"

sans réintroduire un motif qui bloquerait des exemples suivis et non sensibles.

Statut : erreur de configuration confirmée.

Sévérité : moyenne.

## 6. Limite des permissions Claude : garde-fous,
pas confinement absolu
La politique interdit directement :

  "Edit(./requirements.lock)"

Cela bloque l’outil d’édition Claude sur ce fichier.

En revanche, cela n’empêche pas nécessairement une modification effectuée au moyen de :

      • sed ;
      • un script Python ;
      • une commande shell ;
      • un patch approuvé ;
      • une autre forme de commande Bash.

De même, Bash(git push:*) vise les commandes correspondant au motif, mais ne constitue pas un
sandbox général contre toutes les variantes possibles d’une opération Git.

La documentation Claude précise que les règles de permissions contrôlent les appels d’outils
correspondant aux motifs déclarés ; une politique plus stricte peut nécessiter des hooks PreToolUse ,
un sandbox ou une réduction des outils disponibles.

La phrase de CLAUDE.md :

       blocks pushes, lock-file edits and .env reads

est donc légèrement trop absolue.

Recommandation
Employer plutôt :

       The permission policy provides guardrails against direct pushes, lock-file edits and secret-
       file reads. Do not bypass those guardrails through shell commands.

Pour un blocage réellement strict, ajouter un hook qui inspecte les commandes avant leur exécution.

Statut : limite de sécurité, pas erreur de syntaxe.

## 7. Compatibilité Codex — correcte
Codex utilise nativement AGENTS.md pour les instructions propres au dépôt. OpenAI documente
également la possibilité d’utiliser plusieurs fichiers AGENTS.md imbriqués, avec une portée liée aux
répertoires.

Le fichier placé à la racine convient donc pour :

      • Codex CLI ;
      • les tâches Codex portant sur l’ensemble du dépôt ;
      • le partage des commandes et règles avec les autres agents.

Aucun fichier .codex supplémentaire n’est nécessaire pour transmettre ces instructions générales.

Statut : compatible.

Réserve pour Codex cloud
Le contrat impose :

      • création d’un fichier .patch ignoré par Git ;
      • absence de push ;
      • fusion manuelle par le mainteneur.

Cette convention convient très bien à un Codex CLI exécuté localement.

Elle est moins adaptée à un environnement Codex cloud destiné à préparer directement un commit ou
une pull request : le fichier .patch étant ignoré, il ne figure pas dans le diff suivi.

Il serait utile de préciser dans AGENTS.md :

  For local agents, the default deliverable is a numbered patch file.
  When running in a managed PR or cloud workspace, modify the tracked
  working tree and present the resulting diff, but never push unless
  the maintainer explicitly requested that workflow.

Statut : limitation de portabilité, non bloquante pour Codex CLI.

## 8. Compatibilité Kimi K3 — correcte via Kimi
Code CLI
Kimi Code CLI prend en charge un fichier AGENTS.md au niveau du projet et peut même en générer
un avec sa commande d’initialisation.

Le fichier racine sera donc utilisable lorsque Kimi K3 est exécuté à travers Kimi Code CLI dans ce dépôt.

Statut : compatible avec Kimi Code CLI.

Réserve importante
Cette compatibilité appartient au client Kimi Code CLI, pas intrinsèquement au modèle Kimi K3.

Lorsque Kimi K3 est utilisé par :

      • l’API ;
      • une interface web ;
      • un autre IDE ;
      • un orchestrateur tiers ;

rien ne garantit que AGENTS.md soit automatiquement injecté dans son contexte. Dans ce cas, le
client doit explicitement lire ou transmettre le fichier.

La phrase actuelle :

       point any other agent (Codex, Kimi, …) here first — most modern coding CLIs pick this file
       up automatically

est raisonnable, mais pourrait être plus précise :

  Codex and Kimi Code CLI load this file natively. For other clients,
  explicitly provide AGENTS.md as project instructions.

État local Kimi
Kimi Code CLI peut utiliser un état local de projet, notamment sous .kimi-code/ . Il est prudent
d’ignorer les fichiers purement personnels tels que :

  .kimi-code/local.toml

sans ignorer globalement .kimi-code/ , afin de pouvoir suivre plus tard une éventuelle configuration
partagée ou des agents spécialisés.

Statut : amélioration recommandée.

## 9. Erreur de reproductibilité : les outils qualité
ne sont pas installés
AGENTS.md demande de préparer l’environnement avec :

  python3 -m venv .venv
  .venv/bin/pip install --require-hashes -r requirements-test.lock
  mkdir -p var

Il demande ensuite d’exécuter :

  ruff check ...
  bandit ...

Mais Ruff et Bandit appartiennent à :

  requirements-quality.lock

La CI qualité installe explicitement ce verrou avant de lancer les outils.

Sur une machine propre, après avoir suivi uniquement la procédure de AGENTS.md :

      • .venv/bin/ruff n’existe pas ;
      • .venv/bin/bandit n’existe pas ;
      • les commandes système ruff et bandit peuvent être absentes ou avoir une mauvaise
       version.

C’est une erreur de configuration concrète du harness.

Correction recommandée
Installer les deux environnements verrouillés :

  python3 -m venv .venv

  .venv/bin/pip install
    --require-hashes
    -r requirements-test.lock

  .venv/bin/pip install
    --require-hashes
    -r requirements-quality.lock

  mkdir -p var

Puis utiliser systématiquement les exécutables du virtualenv :

  .venv/bin/ruff check alirpunkto tests tools
  .venv/bin/bandit -r alirpunkto tools -ll -q
  .venv/bin/pip-audit --no-deps --ignore-vuln PYSEC-2026-3447

     -r requirements.lock
     -r requirements-test.lock
     -r requirements-quality.lock

Une autre solution consiste à créer deux environnements distincts :

  .venv-test
  .venv-quality

mais cela alourdit la prise en main.

Statut : erreur de configuration confirmée.

Sévérité : moyenne.

## 10. Les commandes du harness ne
correspondent pas exactement à la CI
Ruff
Le harness demande :

  ruff check
    alirpunkto tests tools
    docker/apply_server_overrides.py
    docker/generate_ldif.py

La CI exécute :

  ruff check alirpunkto tests tools

Le harness est ici plus strict que la CI. Ce n’est pas dangereux, mais la différence doit être assumée et
documentée.

Bandit
Le harness demande :

  bandit -q -ll -r alirpunkto

La CI demande :

  bandit -r alirpunkto tools -ll -q

Le harness omet donc tools/ , alors que la CI le contrôle.

Un agent suivant uniquement AGENTS.md pourrait annoncer que Bandit est vert alors que la CI
échoue dans tools/ .

Pip-audit
 AGENTS.md cite la sécurité et les trois workflows, mais ne donne pas la commande locale bloquante
de pip-audit .

Correction recommandée
Créer une section séparant clairement :

  ## Exact CI commands

et :

  ## Additional local checks

Les commandes de la première section doivent être copiées littéralement depuis les workflows.

Statut : incohérence confirmée.

## 11. Aucun test ne verrouille encore le harness
Le dépôt possède de nombreux tests structurels pour :

       • les workflows ;
       • les Dockerfiles ;
       • les verrous ;
       • le transport LDIF ;
       • la configuration Waitress.

Aucun test spécifique ne vérifie actuellement :

       • que .claude/settings.json est du JSON valide ;
       • que CLAUDE.md importe toujours AGENTS.md ;
       • que .env.example reste lisible ;
       • que docker/.env.test est interdit ;
       • que les commandes documentées correspondent à la CI ;
       • que les outils nécessaires sont inclus dans les verrous installés ;

      • que les fichiers locaux Claude et Kimi sont ignorés.

La recherche dans le dépôt ne retourne pas de test consacré à AGENTS.md , CLAUDE.md ou
.claude/settings.json .

Test recommandé
Ajouter :

  tests/test_agent_harness.py

avec au minimum :

     1. chargement JSON de .claude/settings.json ;
     2. présence de @AGENTS.md dans CLAUDE.md ;

     3. vérification de l’interdiction de :

     4. .env ;

     5. docker/.env ;
     6. docker/.env.test ;
     7. docker/secrets/** ;
     8. vérification que .env.example n’est pas bloqué ;
     9. contrôle de la présence de Ruff et Bandit dans requirements-quality.lock ;
   10. comparaison des commandes documentées avec les workflows ;
   11. vérification des entrées .gitignore Claude et Kimi.

Statut : dette de test.

## 12. Correction du chargement de .env depuis la
wheel
Le premier smoke réellement observé a révélé une régression introduite par l’installation sous forme de
wheel.

find_dotenv() recherchait historiquement le fichier en remontant depuis le fichier Python appelant.
Une fois le module installé dans site-packages , cette recherche ne rencontrait plus le .env monté
dans le répertoire de travail du conteneur.

Le code utilise désormais :

  dotenv_path = find_dotenv(usecwd=True) or find_dotenv()
  load_dotenv(dotenv_path)

Cela conserve :

      • le comportement Docker, où .env se trouve dans le répertoire courant ;
      • le repli historique pour les installations hors conteneur.

Un test structurel verrouille cette forme.

Statut : résolu.

## 13. État du smoke Docker
Le message du commit courant indique que la deuxième exécution observable a atteint les résultats
suivants :

      • pile complète démarrée ;
      • conteneurs devenus sains ;
      • requête HTTPS à travers Apache réussie ;
      • échec uniquement lors du dernier test de limitation de connexion.

La cause était l’absence d’en-tête Origin ou Referer dans les requêtes POST HTTPS produites par
curl , alors qu’un navigateur fournit normalement cette information.

Le workflow ajoute maintenant :

  -e "https://${SERVER_NAME}/login"

à son tableau commun curl .

Le test structurel vérifie que cette option reste présente.

Le commit déclare :

      • 1 023 tests réussis ;
      • couverture de 72,10 % ;
      • reproduction locale réussie du test de throttle après l’ajout du Referer.

Ces résultats sont rapportés par le développeur. Le connecteur GitHub ne retourne toujours ni statut
combiné ni exécution associée au SHA actuel. La troisième exécution smoke, avec le correctif Referer,
n’est donc pas indépendamment confirmée ici.

Statut : pile largement validée, dernier workflow complet encore à confirmer.

## 14. Constats applicatifs restant ouverts
Persistance des sanctions
Une nouvelle sanction peut encore être perdue lorsque :

     1. l’écriture côté groupe réussit ;
     2. l’écriture côté membre échoue ;
     3. le passage suivant considère le membre comme autoritatif ;
     4. la sanction uniquement présente côté groupe est supprimée.

Une source autoritative distincte ou une file de reprise reste recommandée.

Sérialisation LDIF
Les valeurs transportées proprement par stdin sont encore insérées dans le LDIF sans sérialisation
complète des retours à la ligne et valeurs nécessitant du base64.

LDAP non chiffré par défaut
La validation des certificats LDAPS existe, mais les piles distribuées utilisent toujours le port 389 sans
TLS par défaut. Ce choix reste explicitement réservé au mainteneur.

Coût du scan des groupes
Le scan effectue encore de nombreuses lectures LDAP par groupe et par membre.

Tâches périodiques
Les rappels restent déclenchés depuis NewRequest , donc dépendants du trafic HTTP et du processus
courant.

.env.example
Le fichier reste obsolète sur les noms des paramètres mail et incomplet sur LDAPS.

Qualité progressive
      • mypy reste informatif ;
      • Ruff reste limité à la famille F ;
      • F841 reste ignorée ;
      • seuil de couverture à 68 % ;
      • Certbot réel non testé ;
      • CSP non activée.

## 15. Priorités révisées
P0 — correction du harness
    1. Remplacer Read(./.env.*) par des chemins sensibles explicites.
    2. Ajouter Read(./docker/.env.test) aux refus.
    3. Installer requirements-quality.lock dans l’environnement documenté.
    4. Utiliser les exécutables .venv/bin/ruff et .venv/bin/bandit .
    5. Aligner exactement les commandes Bandit et Ruff sur la CI.

P1 — verrouillage du harness
    1. Ajouter tests/test_agent_harness.py .
    2. Ajouter .kimi-code/local.toml à .gitignore .
    3. Clarifier Codex local contre Codex cloud.
    4. Clarifier Kimi Code CLI contre les autres clients Kimi K3.
    5. Ajouter éventuellement $schema à .claude/settings.json pour la validation dans les
       éditeurs.

P2 — intégration
    1. Obtenir une exécution smoke entièrement verte après le correctif Referer.
    2. Exécuter le harness depuis une machine ou un conteneur vierge.
    3. Vérifier que chacun des trois agents découvre bien les instructions.
    4. Tester réellement les commandes documentées, sans outil installé globalement.

P3 — application
    1. Persistance transactionnelle des sanctions.
    2. Sérialisation LDIF.
    3. Optimisation du scan LDAP.
    4. Planificateur externe pour les rappels.
    5. Mise à jour de .env.example .
    6. Tests LDAPS, Certbot et CSP.

## 16. Conclusion
Le harness suit la bonne architecture :

     • AGENTS.md constitue un contrat commun reconnu par Codex et Kimi Code CLI ;
     • CLAUDE.md importe correctement ce contrat pour Claude Code ;
     • .claude/settings.json est syntaxiquement valide ;
     • les règles du projet sont précises et reflètent les enseignements des audits précédents ;
     • les adaptations personnelles Claude restent hors Git.

Il existe néanmoins deux erreurs de configuration immédiates :

     1. .env.example est involontairement interdit à Claude ;
     2. docker/.env.test n’est pas interdit.

À cela s’ajoute une erreur de reproductibilité : la procédure d’installation n’installe pas les outils qualité
qu’elle exige ensuite.

Le harness peut donc être utilisé dès maintenant, mais il ne doit pas encore être présenté comme
entièrement fiable ou totalement contraignant.

Évaluation du harness : 7,6/10.

Évaluation globale du dépôt : 8,8/10.

Après correction des permissions Claude, alignement des commandes et ajout d’un test structurel du
harness, la composante multi-agent pourrait atteindre environ 9/10, et la note globale progresser vers
8,9–9,0/10 dès qu’un smoke complet vert sera observable.


