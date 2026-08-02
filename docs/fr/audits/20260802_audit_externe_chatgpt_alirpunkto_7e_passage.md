# Audit externe du dépôt (ChatGPT), septième passage — 2 août 2026

**Provenance.** Septième passage de l'audit statique externe (ChatGPT,
à la demande de Michaël Launay), sur le commit `2c53ef8b` (TLS LDAP,
cache indexé, jeton scellé, validation Keycloak) ; passage précédent
sur `e80f39e`. Note globale proposée : **8,5/10**. Au fil des
passages : 6,5 → 6,9 → 6,7 → 7,1 → 7,8 → 8,2 → 8,5. Texte transmis a
posteriori (le 2026-08-02) et versé pour l'archive : ce document
décrit l'état du dépôt après le train 0073 — les constats « encore
ouverts » ont depuis été traités par 0074 à 0078.

**Statut (rétrospectif).** L'audit valide les quatre corrections du
train 0073 (cache, LDAPS validant, scellement, validation des
réponses) et salue en particulier le test de budget du cookie sur
jeton *difficilement compressible* — « nettement plus fiable qu'un
faux token composé d'un caractère répété ». Quatre suggestions de
valeur durable en ressortent, toujours au carnet : une **clé de
chiffrement dédiée** aux jetons SSO (`SSO_REFRESH_ENCRYPTION_KEY`,
séparation des usages et rotation ciblée — P3) ; la **borne de 90
jours configurable** ou documentée comme politique de plateforme
(P3) ; un test du **véritable en-tête Set-Cookie** produit par la
fabrique Pyramid ; et le banc de **négociation TLS réelle** (CA de
test, slapd sur 636, bind réel, refus d'un mauvais certificat) — qui
rejoint la décision d'exploitation LDAPS, toujours ouverte.

## Suites données

0074 puis 0076 (transport LDIF et cohérence des groupes — les deux
« toujours ouverts » de son P2), 0075 (réserves image), 0078
(appelants). Chroniques dans les versements des 8ᵉ, 10ᵉ et 11ᵉ
passages.

# Texte intégral de l'audit (septième passage)

# Audit actualisé du dépôt AlirPunkto — septième passage

**Date :** 2 août 2026
**Dépôt :** `michaellaunay/alirpunkto`
**Branche :** `master`
**Commit examiné :** `2c53ef8bb5de1cc41debd7faeaabdd207fc6560d`
**Audit précédent :** `e80f39e912e239cc267dda8489bc68cbc57f37ac`

## 1. Résumé exécutif

Le nouveau commit traite quatre constats de sécurité importants :

* validation des certificats des connexions LDAPS ;
* correction du cache global des objets LDAP `Server` ;
* chiffrement du refresh token Keycloak dans la session ;
* validation stricte des réponses des endpoints Keycloak.

Trois constats peuvent désormais être considérés comme résolus :

1. le cache LDAP ne mélange plus des configurations différentes ;
2. le refresh token n'est plus lisible dans le cookie signé ;
3. les réponses Keycloak invalides ne sont plus utilisées sans contrôle.

Le constat « TLS LDAP » n'est que partiellement résolu : lorsque LDAPS
est activé, le certificat est maintenant validé ; mais la pile Docker
générée par défaut utilise toujours LDAP en clair, sur le port 389,
avec `LDAP_USE_SSL=false`.

Le commit annonce 989 tests réussis et une couverture de 71,98 %. Je
n'ai pas pu confirmer indépendamment ces résultats : le connecteur
GitHub n'a retourné aucune exécution Actions ni aucun statut associé à
ce SHA.

## 2. Évaluation actualisée

| Domaine                           | Note précédente | Nouvelle note |
| --------------------------------- | --------------: | ------------: |
| Architecture applicative          |             7,5 |           7,7 |
| Qualité du code                   |             7,6 |           7,8 |
| Tests                             |             8,7 |           9,0 |
| CI et contrôles automatiques      |             9,0 |           9,0 |
| Documentation                     |             8,0 |           8,0 |
| Dépendances et reproductibilité   |             9,0 |           9,0 |
| Sécurité applicative              |             7,7 |           8,6 |
| Sécurité et fonctionnement Docker |             9,0 |           9,0 |
| Exploitation et observabilité     |             7,2 |           7,3 |

**Note globale actualisée : 8,5/10**, contre 8,2/10 précédemment.

# 3. Cache LDAP — résolu

L'ancien code conservait un seul objet global `Server`. Le premier
appel imposait donc son hôte, son port et son mode SSL à tous les
appels suivants.

Le cache est désormais un dictionnaire indexé par
`(server_name, port, bool(use_ssl), str(get_info), mock)`. Deux
configurations différentes produisent donc deux objets distincts,
tandis que deux appels identiques réutilisent le même objet.
`reset_ldap_connection()` vide maintenant l'ensemble du cache.

Les tests vérifient notamment : la résolution des paramètres au moment
de l'appel ; l'absence de connexion LDAP globale partagée ; la
distinction entre deux serveurs ; la réutilisation d'un serveur pour
des paramètres identiques ; l'effacement complet du cache.

**Statut : résolu.**

# 4. Validation des certificats LDAPS — partiellement résolu

## 4.1 Validation cryptographique — résolue

Les connexions LDAPS reçoivent maintenant un objet
`Tls(validate=ssl.CERT_REQUIRED, ca_certs_file=LDAP_CA_CERT_FILE)`.
Lorsque `LDAP_CA_CERT_FILE` n'est pas défini, le code s'appuie sur le
magasin d'autorités de confiance du système. La variable permet
également de désigner un bundle propre au déploiement.

Le test vérifie que le serveur LDAP clair n'a pas de configuration
TLS ; que le serveur LDAPS est différent ; que `use_ssl` est actif ;
que le niveau de validation est `ssl.CERT_REQUIRED`.

La vulnérabilité d'interception par un faux serveur présentant
n'importe quel certificat est donc corrigée pour les connexions LDAPS.

## 4.2 Transport chiffré par défaut — toujours ouvert

Le script d'initialisation génère encore `LDAP_PORT=389` et
`LDAP_USE_SSL=false`. Les identifiants de bind et les données LDAP
circulent donc toujours sans chiffrement dans la configuration Docker
par défaut.

Le réseau Docker backend limite l'exposition, mais ne protège pas
contre : un conteneur compromis sur ce réseau ; une capture réseau sur
l'hôte ; une erreur future de segmentation ; un accès administrateur
local indésirable.

Par ailleurs, la variable `LDAP_CA_CERT_FILE` n'est pas encore
présentée dans `.env.example`, qui continue de documenter l'ancienne
configuration LDAP.

Les tests actuels inspectent l'objet `Tls`, mais n'effectuent pas une
véritable négociation contre un serveur LDAP utilisant un certificat
de test.

**Statut global TLS LDAP : partiellement résolu.**

**Prochaine correction.** La pile de test devrait : 1. générer une
autorité de certification temporaire ; 2. émettre un certificat pour
le service LDAP ; 3. configurer slapd sur le port 636 ; 4. monter le
certificat d'autorité dans Pyramid ; 5. activer `LDAP_USE_SSL=true` ;
6. effectuer un bind réel ; 7. vérifier qu'un certificat incorrect ou
un nom différent est refusé.

# 5. Refresh token Keycloak chiffré — résolu

Le refresh token n'est plus stocké directement dans la session signée.
Il est désormais : encodé en UTF-8 ; compressé avec zlib ; chiffré et
authentifié avec Fernet ; encodé pour son stockage dans la session.

```python
Fernet(get_secret(SECRET_KEY)).encrypt(
    zlib.compress(refresh_token.encode("utf-8"), 9)
)
```

La lecture effectue l'opération inverse. Les cas suivants retournent
`None` : ancien token stocké en clair ; ciphertext modifié ; valeur
qui ne peut pas être décodée ; valeur correctement chiffrée mais non
compressée ; données compressées invalides.

La page d'accueil utilise maintenant exclusivement
`load_sso_refresh_token()`. Une session ancienne ou corrompue provoque
une déconnexion propre plutôt qu'une exception ou l'utilisation d'un
token invalide.

**Budget du cookie.** Le test utilise un token de 2 000 caractères
construit pour être difficilement compressible, puis vérifie que la
session complète reste sous la limite de 4 093 octets avec une marge
supplémentaire. Cette approche est nettement plus fiable qu'un faux
token composé d'un caractère répété, qui aurait artificiellement donné
un excellent taux de compression.

**Statut : résolu.**

**Réserves mineures.**

*Clé partagée.* Le chiffrement réutilise `SECRET_KEY`, déjà employée
pour d'autres fonctions cryptographiques de l'application. Une clé
dédiée (`SSO_REFRESH_ENCRYPTION_KEY`) permettrait une meilleure
séparation cryptographique des usages, la rotation du chiffrement SSO
sans modifier les autres secrets, et une révocation ciblée des
sessions SSO. Il s'agit d'un durcissement recommandé, pas d'un
blocage.

*Test du vrai cookie.* Le test du budget sérialise un dictionnaire
avec pickle et ajoute une estimation de la signature. Il offre une
marge confortable, mais un test complémentaire pourrait vérifier
directement l'en-tête Set-Cookie produit par la fabrique Pyramid
réelle.

# 6. Validation des réponses Keycloak — résolu

Toutes les réponses HTTP 200 des endpoints de tokens passent
maintenant par une fonction commune de validation. Elle impose : une
réponse JSON valide ; un objet JSON ; `access_token` sous forme de
chaîne non vide ; `refresh_token` sous forme de chaîne non vide ;
`expires_in` sous forme d'entier strictement positif ;
`refresh_expires_in` sous forme d'entier strictement positif ; des
durées inférieures ou égales à 90 jours ; le refus explicite des
booléens, même si Python les considère comme des entiers.

Les erreurs sont journalisées sans afficher le corps de réponse,
susceptible de contenir des tokens.

Les tests couvrent : corps non JSON ; JSON qui n'est pas un objet ;
champ absent ; token nul ou inutilisable ; durée sous forme de
chaîne ; durée booléenne ; durée nulle ; durée déraisonnablement
élevée ; chemin d'authentification initial ; chemin de
rafraîchissement.

**Statut : résolu.**

**Réserve opérationnelle.** La limite de 90 jours est codée en dur
(`_MAX_TOKEN_LIFETIME_SECONDS = 90 * 24 * 3600`). Cette politique
convient probablement aux sessions normales, mais peut refuser une
configuration Keycloak légitime utilisant des refresh tokens de plus
de 90 jours, des sessions hors ligne, ou une convention où
`refresh_expires_in=0` représente une absence d'expiration.
L'application ne semble actuellement pas demander le scope
`offline_access`, mais la limite devrait idéalement être configurable
ou documentée comme politique de sécurité de la plateforme.

# 7. Constats de sécurité restant ouverts

## 7.1 Synchronisation bidirectionnelle des groupes LDAP

Les résultats de `conn.modify()` sont désormais vérifiés et
journalisés, mais les deux écritures restent indépendantes (mise à
jour du groupe ; mise à jour du membre). Une écriture peut réussir et
l'autre échouer, créant une divergence entre `uniqueMember` et
`uniqueMemberOf`.

**Statut : partiellement résolu.** Une stratégie de compensation, de
réconciliation autoritative ou de reprise explicite reste nécessaire.

## 7.2 Informations LDIF dans les arguments du processus

`generate_ldif.py` sait lire les mots de passe depuis des variables
d'environnement, et le smoke test utilise correctement ce mécanisme.
Cependant, `docker/init.sh` construit toujours un tableau Bash
contenant les hashes ou mots de passe, les noms et prénoms, les
adresses électroniques, les dates de naissance et les descriptions. Ce
tableau est ensuite développé en arguments positionnels classiques. Il
n'est pas transmis sous forme de variables séparées par NUL,
contrairement au commentaire présent dans le script.

**Statut : partiellement résolu.** La configuration devrait être
transmise par un fichier JSON temporaire en mode 0600, ou l'entrée
standard, ou des descripteurs de fichiers.

## 7.3 Tâche périodique exécutée dans NewRequest

Les rappels aux vérificateurs restent déclenchés dans le cycle des
requêtes HTTP. Cela ne garantit pas une exécution sans trafic, une
coordination multiprocessus, une exécution unique après redémarrage,
ni l'absence de ralentissement de la requête déclenchante.

**Statut : ouvert.**

## 7.4 .env.example obsolète

Le fichier présente encore `MAIL_USE_TLS`/`MAIL_USE_SSL` alors que
l'application lit `MAIL_TLS`/`MAIL_SSL`. Il décrit également
`LDAP_SERVER` comme une URL comprenant le schéma et le port, tandis
que le code utilise un hôte et un port séparés. La nouvelle variable
`LDAP_CA_CERT_FILE` est absente.

**Statut : ouvert.**

# 8. Chaîne de construction : réserves restantes

Les améliorations du passage précédent restent valides : trois verrous
séparés ; hashes ; images multiétapes ; digests des images de base ;
aucun outil de qualité dans le runtime ; smoke test Docker ; Gitleaks ;
audit des trois verrous.

Les réserves suivantes restent ouvertes :

*Installation éditable.* L'application est encore installée avec
`pip install -e .` dans l'image. Une wheel applicative serait plus
adaptée à une image immuable.

*Wheels natives.* Le builder peut compiler une dépendance source, mais
l'image finale ne contient pas nécessairement toutes les bibliothèques
partagées requises. L'usage de `--only-binary=:all:` rendrait cette
hypothèse explicite.

*Paquets APT non figés.* Les images Ubuntu sont épinglées par digest,
mais `apt-get update` et `apt-get install` récupèrent encore les
versions disponibles au moment du build. La construction Python est
fortement reproductible ; la couche système ne l'est pas encore bit à
bit.

# 9. Qualité et dette technique

Les contrôles suivants restent volontairement progressifs : mypy est
informatif et non bloquant ; Ruff ne contrôle que la famille
Pyflakes ; `F841` est encore ignorée ; le seuil de couverture reste
fixé à 68 % ; la CSP reste à activer et tester ; le renouvellement
Certbot n'est pas couvert par le smoke test.

Ces points ne représentent plus des blocages de livraison, mais
constituent la prochaine dette d'industrialisation.

# 10. Priorités révisées

**P0 — fermé** : démarrage Docker ; configuration Waitress ; routage
Apache ; smoke test HTTPS ; détection de secrets.

**P1 — fermé** : verrous séparés ; hashes ; image multiétape ; runtime
minimal ; images de base épinglées.

**P2 — largement traité.** Résolus : cache LDAP ; validation des
certificats LDAPS ; confidentialité du refresh token ; validation des
réponses Keycloak. Toujours ouverts : 1. activer réellement LDAPS dans
la pile de production ; 2. tester une négociation TLS LDAP complète ;
3. rendre la synchronisation des groupes cohérente ; 4. retirer les
données LDIF de `argv`.

**P3 — exploitation** : 1. sortir les rappels de `NewRequest` ;
2. corriger `.env.example` ; 3. documenter et monter les autorités
LDAP privées ; 4. rendre la durée maximale Keycloak configurable ;
5. introduire une clé dédiée au chiffrement des refresh tokens.

**P4 — finition** : 1. construire une wheel de l'application ;
2. figer ou snapshotter les dépendances APT ; 3. imposer les wheels
Python ; 4. rendre mypy progressivement bloquant ; 5. augmenter Ruff
et la couverture ; 6. tester Certbot et la CSP.

# 11. Conclusion

Le commit `2c53ef8…` ferme plusieurs des risques applicatifs les plus
importants encore présents.

Les progrès les plus significatifs sont : un serveur LDAPS ne peut
plus être accepté sans validation de certificat ; une configuration
LDAP ne pollue plus les connexions utilisant d'autres paramètres ; le
refresh token n'est plus exposé en clair dans le cookie ; une réponse
Keycloak malformée ou incohérente est rejetée proprement.

Le principal point de nuance concerne LDAP : le mécanisme LDAPS est
maintenant sûr lorsqu'il est activé, mais la pile fournie continue
d'utiliser LDAP sans chiffrement par défaut.

Les risques majeurs se concentrent désormais sur : le transport LDAP
réellement déployé ; la cohérence des écritures de groupes ; les
données sensibles transmises par `argv` ; les tâches périodiques ;
quelques aspects de reproductibilité et de politique de sécurité.

**Évaluation actuelle : 8,5/10.**

Une note autour de 8,8 à 9,0/10 deviendrait justifiée après activation
et test de LDAPS dans Compose, correction du générateur LDIF et
sécurisation transactionnelle des groupes LDAP.
