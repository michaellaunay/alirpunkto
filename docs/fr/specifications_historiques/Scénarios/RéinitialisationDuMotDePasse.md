# Réinitialisation du mot de passe

## Résumé

L'utilisateur demande à réinitialiser son mot de passe.

## Acteurs

- L'utilisateur
- L'administrateur
- Le serveur OpenLDAP
- Le serveur de messagerie

## Étapes

1. Un utilisateur se connecte à la page de login d'AlirPunkto.
2. AlirPunkto affiche la page de login.
3. L'utilisateur clique sur "Mot de passe oublié".
4. AlirPunkto affiche une page demandant l'identifiant ou l'adresse e-mail du membre.
5. L'utilisateur saisit l'identifiant ou l'adresse e-mail.
6. L'utilisateur confirme la réinitialisation.
7. AlirPunkto prépare un e-mail contenant un lien sécurisé pour la modification du mot de passe.
8. AlirPunkto envoie un e-mail de réinitialisation du mot de passe à l'adresse du membre.
9. L'utilisateur ouvre son e-mail.
10. L'utilisateur clique sur le lien de réinitialisation.
11. Le navigateur demande à AlirPunkto la page de réinitialisation.
12. AlirPunkto déchiffre le token et transmet la vue de saisi du nouveau mot de passe.
13. L'utilisateur saisit le nouveau mot de passe et le confirme.
14. AlirPunkto génère le nouveau `hash`` associé au mot de passe et met à jour l'entrée OpenLDAP.
15. AlirPunkto affiche la page de succès..

## Exigences

### Exigence de sécurité

Le lien de modification du mot de passe doit avoir les caractéristiques suivantes :
- Durée de péremption inférieure à 24 heures.
- Chiffrement fort du token de réinitialisation : l'usage de la force brute ne doit pas permettre de connaître le mécanisme de chiffrement.
- Nombre de tentatives de réinitialisation limitées.
- Envoi d'un e-mail à l'administrateur en cas de tentative de force brute.

La page de login pour la réinitialisation ne doit pas permettre de savoir si l'e-mail ou l'identifiant saisis existent ou non. Il ne doit pas y avoir de message annonçant l'envoi d'un e-mail, mais un message de type "Si l'identifiant ou l'adresse saisie existe, alors vous avez reçu un e-mail." Cela est fait pour éviter qu'il soit possible de déterminer les identifiants ou adresses existants.