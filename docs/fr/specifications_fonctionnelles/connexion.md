# Connexion

> Statut : spécification fonctionnelle courante (remplace le scénario
> historique `Connexion d'un Membre.md`).
> Modules : `alirpunkto/views/login.py`, `alirpunkto/views/sso_login.py`,
> `alirpunkto/views/home.py`.

## Par formulaire (`/login`)

1. Le membre saisit pseudonyme et mot de passe.
2. Le pseudonyme est résolu en `oid` ; l'authentification est un **bind
   LDAP** (`check_password`) — aucun mot de passe n'est comparé côté
   application.
3. En cas de succès : synchronisation du membre depuis LDAP
   (`update_member_from_ldap`, recréation comprise si la ZODB est neuve),
   ouverture de session (`logged_in`, objet `User` léger), obtention d'un
   jeton Keycloak pour aligner le SSO, puis redirection vers la page
   initialement demandée.
4. En cas d'échec : message neutre « identifiant ou mot de passe invalide »
   (pas d'indice sur l'existence du compte).

## Par SSO (`/sso_login`)

Flux OIDC Keycloak : redirection, authentification chez Keycloak, retour
avec code, vérification du jeton (signature, audience, expiration), puis
mêmes étapes de synchronisation et d'ouverture de session. La session ne
conserve que le jeton de rafraîchissement et son échéance
(cf. [../architecture/05_authentification.md](../architecture/05_authentification.md)).

## Session ouverte

La page d'accueil prolonge la session SSO tant que le jeton de
rafraîchissement est valable, sinon déconnecte proprement. `/logout` purge
la session.

## Cas particuliers

- Un membre présent dans LDAP mais absent de la ZODB (base reconstruite)
  est **recréé à la volée** à sa première connexion, type et profil
  compris.
- L'administrateur LDAP (`is_admin`) dispose d'un chemin dédié sans compte
  membre.
