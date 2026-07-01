# Résumé

Scénario d'accès à la page d'accueil avec affichage des applications tierces.

# Acteurs

**Membre**: L'utilisateur authentifié d'AlirPunkto.
 **Administrateur**: L'administrateur du système qui gère l'identification et la navigation vers les applications tierces.

## Données

- **username**: Nom d'utilisateur, chaîne de caractères.
- **password**: Mot de passe, chaîne de caractères.
- **applications**: Liste des applications tierces par exemple (Drupal, Elgg, KuneAgi, LimeSurvey, LiquidFeedback, Mattermost, Moodle, NextCloud + Collabora, SYMPA), énuméré.

### Étapes

1. Le Membre ouvre le site d'AlirPunkto ;
2. AlirPunkto affiche la page de connexion ;
3. Le Membre entre son `username` et `password` ;
4. AlirPunkto valide les informations d'identification ;
5. Si les informations d'identification sont correctes :
    1. AlirPunkto charge la page d'accueil personnalisée pour le Membre ;
    2. AlirPunkto affiche les liens vers les applications tierces (`applications`) ;
    3. Le Membre peut cliquer sur n'importe quel lien pour accéder à l'application tierce correspondante ;
    4. AlirPunkto dirige le Membre vers l'application tierce sélectionnée ;
6. Fin du scénario.

### Scénarios Alternatifs

#### Informations d'Identification Incorrectes
- Si les informations d'identification sont incorrectes, AlirPunkto affiche un message d'erreur ;
- Le Membre peut essayer de se reconnecter ou récupérer son mot de passe ;
- Fin du scénario alternatif.

#### Accès Direct à la Page d'Accueil sans Identification
- Si le Membre tente d'accéder directement à la page d'accueil sans s'être identifié, AlirPunkto redirige vers la page de connexion ;
- Fin du scénario alternatif.