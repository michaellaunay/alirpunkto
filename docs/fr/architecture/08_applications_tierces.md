# Applications tierces

> Statut : documentation courante.
> Modules : `alirpunkto/views/home.py`, configuration `.ini`
> (`applications.*`), `alirpunkto/views/sso_login.py`.

## Principe

AlirPunkto est le point d'entrée des membres vers les services de la
coopérative (listes de diffusion, forums, outils). Les applications ne sont
pas codées en dur : elles sont **déclarées dans la configuration** et
présentées sur la page d'accueil aux membres connectés.

## Déclaration

Chaque application est décrite par des clés préfixées dans le fichier
`.ini` :

```ini
applications.sympa.name = Sympa
applications.sympa.id = sympa
applications.sympa.logo_file = static/sympa.png
applications.sympa.url = https://listes.example.coop/sso/keycloak
applications.sympa.description = Listes de diffusion
applications.sympa.explanation = Gère tes abonnements aux listes.
```

Ces entrées sont regroupées au démarrage et exposées aux vues via
`request.registry.settings["applications"]` ; `home_view` les affiche avec
leur logo et leur lien. Deux règles issues du terrain (#142, #147) :

- `url` doit être **l'URL d'entrée SSO** de l'application (le point
  d'aboutissement Keycloak), pas sa page de connexion générique — sinon le
  membre retombe sur un formulaire de mot de passe qu'il n'a pas ;
- l'`explanation` s'affiche en texte sous le lien (plus en info-bulle), et
  chaque lien s'ouvre dans un nouvel onglet
  (`target="_blank" rel="noopener noreferrer"`).

Les clés `name`, `id`, `logo_file` et `url` sont **requises** :
`__init__.py` écarte silencieusement toute application incomplète. Des
tests d'invariants structurels vérifient les `.ini` du dépôt (déclarations
analysables, clés requises, URL absolues) sans figer les valeurs propres à
chaque déploiement.

## Accès unifié

L'accès aux applications repose sur le SSO : les applications tierces sont
des clients **Keycloak**, adossé au même annuaire OpenLDAP qu'AlirPunkto.
Un membre connecté à AlirPunkto est donc reconnu par les applications sans
nouvelle saisie de mot de passe (voir
[05_authentification](05_authentification.md)).

## Historique

Les scénarios initiaux « Liste des Applications » et « Configuration de la
liste des applications » sont archivés dans
`../specifications_historiques/Scénarios/` ; le présent document et la
spécification fonctionnelle courante les remplacent.
