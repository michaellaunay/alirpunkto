# Candidature

## Résumé
Détaille la procédure d'inscription

## Acteurs

- Le candidat ;
- Le serveur Open LDAP
- Le serveur de messagerie
- L'administrateur
- Les membres actifs

## Prérequis

## Étapes 

Le Candidat se connecte à AlirPunkto ;  
AlirPunkto retourne la page d'accueil avec le lien d'inscription ;  
Le candidat demande à créer un compte ;  
AlirPunkto demande à résoudre un `captcha`;  
AlirPunkto affiche le formulaire d'inscription ;  
Le candidat saisit les informations demandées ;  
Le candidat soumet le formulaire ;  
AlirPunkto vérifie la syntaxe des saisies ;  
AlirPunkto interroge LDAP pour vérifier que le pseudo n'est pas déjà utilisé ;  
AlirPunkto interroge LDAP pour vérifier que le mail n'est pas déjà utilisé ;  
Si le pseudo ou le mail sont déjà utilisés alors le candida est déjà inscrit et AlirPunkto affiche un message d'erreur ;  
Si le candidat n'est pas déjà inscrit :  
	AlirPunkto crée un Objet Candidature avec les informations du formulaire ;  
	AlirPunkto attribue un OID à cet objet ;  
	AlirPunkto met l'état de la candidature à `Email validation`;  
	AlirPunkto enregistre la date ;  
	AlirPunkto enregistre en ZODB cet objet ;  
	AlirPunkto envoie un e-mail de demande de confirmation de soumission de la candidature au candidat ;  
	AlirPunkto positionne une tache nettoyage de la candidature si échéance atteinte ;  
	AlirPunkto affiche la page indiquant que le candidat va recevoir un mail et qu'il doit suivre le lien de confirmation de son adresse e-mail ;  

Le candidat reçoit le e-mail et clique sur le lien de confirmation ;  
AlirPunkto rentre dans la vue de soumission de la candidature ;  
AlirPunkto prévient le candidat qu'il doit déposer une copie de sa pièce d'identité sur le site ;

AlirPunkto indique au candidat que sa pièce d'identité sera chiffrée par son navigateur avec les clés des vérificateurs tirés au sort et qu'en conséquence, seule une version chiffrée de celle-ci sera stockée sur AlirPunkto ;  
AlirPunkto tire au sort 3 vérificateurs parmi les membres du LDAP si possible, sinon l'administrateur ;
AlirPunkto enregistre les vérificateurs dans le dictionnaire `voters` de l'objet candidature ;  
AlirPunkto enregistre la date de soumission de la candidature ;  
AlirPunkto ajoute un attribut "status" qui vaut "pending" par défaut ;  
AlirPunkto ajoute un attribut "votes" qui est un dictionnaire vide ;  
AlirPunkto enregistre les modifications de l'objet candidature dans la ZODB ;  
AlirPunkto envoie un mail de demande de vote (template vote.pt en passant l'identifiant de la candidature) pour accepter ou non la candidature aux vérificateurs ;  
Si l'envoi du mail échoue, le site log un message d'erreur et essaye d'envoyer un mail à l'administrateur ;  
AlirPunkto transmet au navigateur du Candidat les clés publiques des vérificateurs et lui demande de téléverser sa pièce d'identité signée ;  

Les vérificateurs reçoivent leur mail et cliquent sur le lien de vote ;  
AlirPunkto tente d'afficher la vue de vote ;  
Si les vérificateurs ne sont pas authentifiés, AlirPunkto affiche la page d'authentification ;  
Le vérificateur s'authentifie ;  
AlirPunkto affiche la page de vote avec le lien vers la pièce d'identité chiffrée ;  
Le vérificateur demande à consulter la pièce ;  
AlirPunkto transmet au navigateur la pièce chiffrée ;  
Le navigateur du vérificateur demande le mot de passe pour déchiffrer la pièce ;  
Le vérificateur saisit son mot de passe ;  
Le navigateur déchiffre et affiche la pièce d'identité ;  
Le vérificateur accepte ou refuse la candidature ;  
AlirPunkto enregistre le choix du vérificateur ;  
Si le dernier vérificateur a voté alors AlirPunkto détermine si la candidature est acceptée ou non ;  
Alir Punkto enregistre le résultat dans l'objet et l'enregistre dans la ZODB ;  
Si elle est acceptée :  
	AlirPunkto ajoute une entrée dans LDAP ;  
	AlirPunkto envoie un mail de félicitation au nouveau membre ;  
	AlirPunktoChange l'état de la Candidature à `Approved` ;  
	AlirPunkto enregistre la `Candidature` dans la ZODB ;  
Si elle est refusée :  
	AlirPunkto enregistre l'état de la Candidature à `Approved` ;  
	AlirPunkto enregistre la `Candidature` dans la ZODB ;  
	AlirPunkto envoie un mail de refus au nouveau membre ;  

AlirPunkto affiche un message de succès et invite le candidat à vérifier sa boîte mail pour connaître le résultat de sa candidature.

## Scénarios alternatifs

### L'utilisateur ne reçoit pas le mail ou ne confirme jamais
Le scheduleur d'AlirPunkto cherche les sousmissions ayant dépassé la date d'échéance :
    Si la candidature a reçu plus de vote favorable alors traitement favorable (C.f. ci dessu)
    sinon traitement du refus.

## Datas


## Divers

### Exemple de scheduler

```python
import atexit
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.start()
scheduler.add_job(print_greetings,
    id='greetings', 
    name='Send out birthday greetings', 
    trigger='cron', 
    minute=0, 
    hour=12,
)

atexit.register(lambda: scheduler.shutdown())
```

### Représentation 

```mermaid
classDiagram
    class RegisterForm {
        -fullname: String
        -birthdate: Date
        -nationality: String
        -cooperative_number: String
        -pseudonym: String
        -email: String
        -lang1: String
        -lang2: String
        -usual_name: String
        -usual_surname: String
        -postal_code: String
        -city: String
        -country: String
    }
```

### Prototype d'interface utilisateur

Prototype d'interface utilisateur pour le formulaire avec PlantUML et l'extension Salt :

```plantuml
@startsalt
{
  {T
    "Full Name           : " | [                      ]
    "Birth Date          : " | [                      ]
    "Nationality         : " | [                      ]
    "Cooperative Number  : " | [                      ]
    "Pseudonym           : " | [                      ]
    "Email               : " | [                      ]
    "First Interaction Language : " | [                      ]
    "Second Interaction Language: " | [                      ]
    "Usual Name          : " | [                      ]
    "Usual Surname       : " | [                      ]
    "Postal Code         : " | [                      ]
    "City                : " | [                      ]
    "Country             : " | [                      ]
  }
  [Submit]
}
@endsalt
```
