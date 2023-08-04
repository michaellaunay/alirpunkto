# Résumé

Scénario de consultation et de gestion des candidatures par l'administrateur dans AlirPunkto.

# Acteurs

1. **Administrateur**: L'utilisateur avec les droits d'administration d'AlirPunkto.
2. **AlirPunkto**: L'application AlirPunkto.
3. **Candidature**: Une entité représentant une candidature au sein d'AlirPunkto.

# Données

- **candidature_id**: Identifiant unique de la candidature, chaîne de caractères.
- **state**: État de la candidature (par exemple, "EmailValidation", "Pending"), énuméré.
- **verifiers_list**: Liste des vérificateurs associés à la candidature, ensemble de chaînes de caractères.
- **applicant_name**: Nom du candidat, chaîne de caractères.

# Étapes

1. L'Administrateur se connecte à l'application AlirPunkto avec ses identifiants ;
2. L'Administrateur navigue jusqu'à la section d'administration dédiée à la gestion des candidatures ;
3. AlirPunkto affiche une liste des candidatures incluant les informations `oid`, `state`, `verifiers_list`, et `name` ;
4. L'Administrateur peut trier, filtrer, et chercher des candidatures spécifiques en utilisant les outils de navigation et de recherche fournis par AlirPunkto ;
5. L'Administrateur sélectionne une candidature spécifique pour voir plus de détails ;
6. AlirPunkto affiche les détails complets de la candidature sélectionnée ;
7. L'Administrateur peut choisir de relancer l'un ou plusieurs vérificateurs si la candidature est en état "Pending" ;
   a. AlirPunkto envoie un e-mail de relance aux vérificateurs sélectionnés ;
   b. Le système met à jour l'état de la relance pour la candidature spécifique ;
8. L'Administrateur continue la navigation ou termine la consultation et se déconnecte si nécessaire ;
9. Fin du scénario.

# Scénarios Alternatifs

## Aucune Candidature Trouvée

- Si aucune candidature ne correspond aux critères de l'Administrateur, un message indiquant qu'aucune candidature n'a été trouvée est affiché.

## Erreur lors de l'Envoi de la Relance

- Si une erreur se produit lors de l'envoi de la relance aux vérificateurs, un message d'erreur est affiché à l'Administrateur ;
- L'Administrateur peut essayer de réexécuter l'action ou contacter le support technique si le problème persiste.

# Contraintes

- L'accès aux candidatures et aux actions de relance doit être sécurisé et réservé aux administrateurs autorisés.
- Les transitions d'état et les actions de relance doivent être conformes aux règles et aux flux de travail définis pour les candidatures au sein d'AlirPunkto.
- La communication avec les vérificateurs doit être effectuée de manière appropriée et conforme aux politiques de communication de l'organisation.