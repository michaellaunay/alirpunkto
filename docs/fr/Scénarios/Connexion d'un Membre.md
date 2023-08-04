# Résumé

Scénario détaillé pour la connexion (login) d'un membre dans le système :

# Acteurs

- Membre
- Système AlirPunkto

# Données

- Identifiant (courriel ou pseudonyme)
- Mot de passe

# Étapes

1. Le membre accède à la page de connexion d'AlirPunkto.
2. Le membre saisit son identifiant, qui peut être son courriel ou son pseudonyme.
3. Le membre saisit son mot de passe associé.
4. Le membre clique sur le bouton "Se connecter".
5. AlirPunkto vérifie les informations fournies.
6. Si l'identifiant ou le mot de passe est incorrect, un message d'erreur est affiché, et le membre a la possibilité de réessayer.
7. Si l'identifiant et le mot de passe sont corrects, le processus continue.
8. Le membre est authentifié et redirigé vers la page d'accueil personnalisée d'AlirPunkto.
9. La session du membre est active, et il a maintenant accès aux fonctionnalités réservées aux membres, telles que les applications tierces (Drupal, Elgg, KuneAgi, LimeSurvey, LiquidFeedback, Mattermost, Moodle, NextCloud + Collabora, SYMPA, etc.).

# Scénario alternatif

## Option de Récupération de Mot de Passe

   Si le membre oublie son mot de passe, il peut cliquer sur un lien "Mot de passe oublié?" sur la page de connexion.
   Le système guidera le membre à travers un processus de récupération de mot de passe, y compris la vérification de son identité via son adresse e-mail.