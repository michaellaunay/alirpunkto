# Résumé

Scénario de configuration de la liste des applications par l'administrateur.

# Acteurs

1. **Administrateur**: L'utilisateur avec les droits d'administration du système.
2. **Système Ubuntu**: Le système d'exploitation hébergeant AlirPunkto.

# Étapes

1. L'Administrateur se connecte au système d'exploitation hébergeant AlirPunkto ;
2. L'Administrateur ouvre un éditeur de texte avec des droits d'administrateur pour accéder aux fichiers de configuration `development.ini` ou `deployment.ini` ;
3. L'Administrateur navigue jusqu'à la rubrique "Applications" dans le fichier de configuration choisi ;
4. Sous la rubrique "Applications", l'Administrateur peut voir la liste actuelle des applications avec leurs `application_name`, `description`, `logo`, et `link` ;
5. L'Administrateur peut ajouter, modifier ou supprimer des applications :
    1. Pour ajouter une application, l'Administrateur entre le `application_name`, `description`, `logo`, et `link` ;
    2. Pour modifier une application, l'Administrateur sélectionne l'application et met à jour les informations nécessaires ;
    3. Pour supprimer une application, l'Administrateur supprime les lignes correspondant à l'application ;
6. L'Administrateur sauvegarde les modifications dans le fichier de configuration ;
7. Si nécessaire, l'Administrateur redémarre AlirPunkto pour appliquer les modifications.

# Scénarios Alternatifs

## Erreur de Droits d'Accès

- Si l'Administrateur n'a pas les droits d'accès nécessaires, le système Ubuntu affiche un message d'erreur ;
- L'Administrateur peut essayer de se reconnecter avec des droits d'administrateur appropriés.

# Contraintes

- Les modifications apportées au fichier de configuration directement peuvent nécessiter une compréhension de la syntaxe et du format YAML du fichier. Une erreur dans le fichier de configuration peut entraîner des problèmes avec AlirPunkto. Il est donc recommandé que seuls les administrateurs expérimentés modifient ces fichiers directement.

# Données

- **application_name**: Nom de l'application, chaîne de caractères.
- **description**: Description de l'application, chaîne de caractères.
- **logo**: Chemin vers le fichier du logo de l'application, chaîne de caractères.
- **link**: Lien vers l'application, chaîne de caractères.