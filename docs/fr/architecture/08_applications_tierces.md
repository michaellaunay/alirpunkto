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
applications.sympa.logo_file = static/sympa.png
```

Ces entrées sont regroupées au démarrage et exposées aux vues via
`request.registry.settings["applications"]` ; `home_view` les affiche avec
leur logo et leur lien.

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
