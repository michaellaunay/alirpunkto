# Résumé

Scénario de désabonnement

# Étapes

1. Le Membre se connecte à AlirPunkto ;
2. AlirPunkto retourne la page de profil du Membre ;
3. Le Membre demande à désactiver son compte ;
4. AlirPunkto affiche une page de confirmation avec les implications du désabonnement ;
5. Si le Membre confirme :
    1. AlirPunkto change l'état de l'objet `membership` de type `Membership` à l'état "PendingUnsubscription", et enregistre la demande ;
    2. AlirPunkto enregistre en base de données le changement d'état ;
    3. AlirPunkto prépare un e-mail à destination du Membre contenant un lien de confirmation pour désactiver le compte ;
    4. AlirPunkto envoie l'e-mail au Membre ;
    5. AlirPunkto affiche un message prévenant le Membre qu'il doit suivre le lien de confirmation dans son e-mail ;
6. Le Membre ouvre le mail reçu et clique sur le lien de confirmation ;
7. AlirPunkto valide le lien et change l'état de la `membership` à "Unsubscribed" ;
8. AlirPunkto enregistre en base de données le changement d'état ;
9. AlirPunkto envoie un e-mail de confirmation de désabonnement au Membre ;
10. AlirPunkto supprime les données personnelles du Membre conformément aux régulations en vigueur ;
11. AlirPunkto revient sur la page d'accueil ;
12. Fin du scénario.

# Scénarios alternatifs

## Le Membre annule la demande de désabonnement

- Le Membre décide d'annuler la demande de désabonnement ;
- AlirPunkto conserve l'état de `membership` tel qu'il était avant la demande de désabonnement ;
- AlirPunkto enregistre en base de données le changement d'état ;
- AlirPunkto revient sur la page de profil du Membre .

## Arrivée à échéance de la confirmation de désabonnement

- Le Membre ne confirme pas la désactivation du compte dans le délai imparti ;
- Le scheduleur d'AlirPunkto cherche les `memberships` dans l'état "PendingUnsubscription" arrivées à échéance ;
- AlirPunkto annule la demande de désabonnement et retourne le `membership` à son état précédent ;
- AlirPunkto enregistre en base de données le changement d'état ;
- AlirPunkto peut choisir d'envoyer un e-mail au Membre pour l'informer de l'expiration de la demande.