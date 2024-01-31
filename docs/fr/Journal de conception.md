# 2023-07-22

Le fonctionnement par simple candidature sans vérification du mail avant soumission est une faille dans le sens où les électeur peuvent ainsi être soumis à des candidatures qui sont des spams.
Pour éviter cela il faut modifier la conception de la vue `register.py` pour ajouter dans le scnério de candidature l'envoi du mail de confirlation de candidature. [[Candidature]]

@TODO
Ajouter le scheduler voir [pyramid_scheduler](https://pypi.org/project/pyramid_scheduler/) ou https://stackoverflow.com/questions/28584597/python-pyramid-periodic-task

@TODO
Check le markdown des docs

# 2023-07-17 à 2023-07-28

Michaël Launay : J'éclate complètement le code en plusieurs fichiers et crée les répertoires Schema, j'ajoute la récupération de la liste des applications.
@TODO traductions 
@TODO déboguer
@TODO écriture des tests unitaires
@TODO remplacer l'envoi de mail par Pyramid Mailer
# 2023-07-31

La solution consistant à téléverser ou transmettre par mail des numérisations de pièce d'identité n'est pas très satisfaisante, car elle envoie en clair par messagerie une pièce d'identité aux membres vérificateurs.
Ce n'est pas un processus de validation qui respecte la confidentialité à la fois de la pièce d'identité mais si elle se fait par mail en plus elle permet au candidat de connaître l'adresse mail de membres certifiés sans qu'on sache encore qui est cette personne.
Il y a donc un risque que le candidat puisse faire pression sur les vérificateurs.
Un vérificateur pourra nous reprocher d'avoir diffusé son adresse.

Pour régler cela nous avons plusieurs solutions :

- utiliser des proxy mail pour les adresses des vérificateurs et un chiffrement de la pièce par le candidat.

- chiffrer la pièce d'identité côté navigateur du candidat avec les clés publiques associés au compte des vérificateurs et déposer les documents chiffrés sur le portail (une variante consiste à utiliser des mécanismes d"enveloppes chiffrés contenant la clé de déchiffrement du document).

Il existe déjà des bibliothèques pour faire cela qui permettent de chiffrer des documents côté navigateur avant de les déposer sur un serveur web. Ces solutions utilisent généralement des bibliothèques de chiffrement en JavaScript pour effectuer le chiffrement localement, garantissant ainsi que les données restent sécurisées avant d'être envoyées au serveur. Plusieurs bibliothèques populaires permettent de chiffrer des documents côté navigateur :

1. CryptoJS : CryptoJS est une bibliothèque JavaScript de chiffrement qui prend en charge différents algorithmes de chiffrement, tels que AES, DES, Triple DES, etc. Vous pouvez l'utiliser pour chiffrer vos données avant de les envoyer au serveur.

Site web : [https://cryptojs.gitbook.io/docs/](https://cryptojs.gitbook.io/docs/)

2. sjcl (Stanford JavaScript Crypto Library) : C'est une bibliothèque JavaScript de chiffrement développée par Stanford University. Elle propose des implémentations de plusieurs algorithmes de chiffrement et de hachage.

Site web : [https://bitwiseshiftleft.github.io/sjcl/](https://bitwiseshiftleft.github.io/sjcl/)

3. Forge : Forge est une bibliothèque JavaScript complète qui prend en charge le chiffrement, le hachage, les signatures numériques, etc. Elle est souvent utilisée pour les tâches de chiffrement côté navigateur.

Site web : [https://github.com/digitalbazaar/forge](https://github.com/digitalbazaar/forge)

4. WebCrypto API : L'API WebCrypto est une spécification du World Wide Web Consortium (W3C) qui fournit une interface native pour le chiffrement en JavaScript. Elle permet d'accéder aux fonctionnalités de chiffrement directement via le navigateur sans avoir besoin de bibliothèques tierces.

Documentation : [https://developer.mozilla.org/en-US/docs/Web/API/Web_Crypto_API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Crypto_API)

Avec ce système, on applique ce que l'on appelle un chiffrement de bout en bout.

# 2023-08-01

Le scénario Candidature est simplifié du chiffrement de bout en bout et les parties suivantes sont simplifiées:

Scénario Candidature avec chiffrement de bout en bout (le plus simple est d'utiliser une enveloppe en asymétrique et d'y mettre la clé de déchiffrement symétrique du document, voir demain pour complément de réflexion)

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

## Les échanges avec Vincent sur le chiffrement de bout en bout :

```
Michaël Launay  [17 h 18]

Salut Vincent, que peux tu me dire de ce que j'ai écris à Laurent à propos de l'identification des nouveaux membres sur sa plateforme : Voici une réflexion que j'ai eu ce matin à propos de la création de compte par des "candidats" dont l'identité va devoir être vérifiée sur l'application AlirPunkto que je développe en python Pyramid et bootstrap 5. On a deux problèmes qui peuvent être résolu de la même façon. Le 1er avec le système d'authentification actuel. Le mot de passe du candidat est envoyé à Alirpunkto lors de son enregistrement. Alirpunkto calcul un hash avec le mot de passe et n'enregistre sur disque que cette valeur de "hachage" du mot de passe. Lors des tentatives de connexions, Alirpunkto utilise la même procédure de "hachage" pour vérifier que le mot de passe saisit est bien le même en comparant les deux valeurs de hash. Celle stockée et celle qui vient d'être générée. Cela résout une partie du problème mais on constate que l'on a une circulation du mot de passe vers le serveur. On peut via des bibliothèques Java Script calculer le hash directement sur le navigateur du membre et ne transmettre que cette valeur de hash. JavaScript permet de faire cela de façons automatique et transparente côté navigateur. Cela marche car la fonction de hachage est univoque et produit donc toujours la même sortie pour la même entrée. 2nd problème, le stockage de la pièce d'identité. Je propose à partir des algorithmes de chiffrement classiques de développer une fonction univoque qui à partir d'un mot de passe créé toujours la même paire de clé publique privée. Nous pouvons alors lors de la candidature utiliser le mot de passe saisit dans le formulaire pour générer localement dans le navigateur les clés et transmettre la clé publique lors de l'envoi du formulaire du mot de passe. Alirpunkto stocke alors la valeur de hachage du mot de passe et la clé publique. Cela de façon automatique et transparente. La valeur de hachage sera utilisée pour comparaison avec les valeurs reçues lors des connexions et ne quittera donc jamais le serveur. La clé publique sera envoyée aux candidats lorsque le membre déposera sa pièce d'identité. (C'est la raison pour laquelle on utilise à la fois le "hash" et la clé publique). Lors de la validation de la pièce d'identité, la page demande au membre son mot de passe et génère la clé privée pour déchiffrer le document. Ici on utilise la propriété d'unicité de la génération des clés pour ne pas avoir à utiliser un stockage de clé et donc pouvoir faire cela du côté client, dynamiquement et sans que le membre ne voit autre chose qu'un sablier et un message indiquant le déchiffrement du document.

Michaël Launay [17 h 19]

Voici ce qu'en dit gpt 4: mais je suis sur ma faim : Votre réflexion sur la manière de traiter l'authentification et le stockage de données sensibles comme la pièce d'identité est intéressante et montre une réelle préoccupation pour la sécurité des données utilisateur. Cependant, il y a quelques points qui méritent une discussion plus approfondie.  

1. **Hachage du mot de passe côté client** : Bien que l'idée de hacher le mot de passe côté client puisse sembler attrayante, elle présente en réalité quelques problèmes potentiels. Le hachage côté client peut offrir une protection supplémentaire contre l'interception du mot de passe sur le réseau, mais si le hash lui-même est compromis, il peut être utilisé pour s'authentifier auprès du serveur. En pratique, si le serveur attend le hash du mot de passe plutôt que le mot de passe lui-même, le hash devient effectivement le mot de passe. De plus, si un attaquant compromet le site Web et modifie le code JavaScript, il peut simplement désactiver le hachage et collecter les mots de passe en clair.
2. **Génération de clés de chiffrement basée sur le mot de passe** : Utiliser le mot de passe pour générer une paire de clés publique/privée est une idée intéressante, et c'est un concept connu dans la cryptographie appelé dérivation de clé. Toutefois, cette méthode a ses propres défis. Les mots de passe des utilisateurs ne sont généralement pas suffisamment aléatoires ou longs pour constituer des clés cryptographiques sûres sans traitement supplémentaire. Il existe des fonctions de dérivation de clé spécialement conçues pour ce but, comme PBKDF2, qui peuvent être utilisées pour convertir un mot de passe en une clé sûre.
3. **Stockage et accès aux documents d'identité** : L'utilisation du chiffrement pour protéger les documents d'identité est absolument essentielle. Cependant, le système que vous proposez où le document est déchiffré uniquement par le client nécessiterait que le client stocke quelque part la clé privée ou la recrée à chaque fois à partir du mot de passe. Si la clé est perdue ou si le mot de passe est oublié, le document serait irrécupérable. Une solution pourrait être d'utiliser une clé symétrique pour chiffrer le document, puis de chiffrer cette clé symétrique avec la clé publique de l'utilisateur. Le serveur pourrait alors déchiffrer la clé symétrique avec la clé privée correspondante lorsqu'il a besoin d'accéder au document.

En somme, bien que vos réflexions soient très pertinentes, elles soulèvent des questions complexes qui nécessitent une réflexion et une analyse plus approfondies pour garantir que les solutions proposées ne créent pas de nouveaux problèmes ou vulnérabilités. Collaborer avec un spécialiste en sécurité informatique pourrait être une excellente idée pour valider et affiner ces concepts.

Vincent F  [17 h 27]

Salut, il a pas tord dans ses réponses

Michaël Launay  [17 h 29]

Oui mais je suis très embêté avec le stockage des pièce d'identité sur le serveur. Et je pensais régénérer la clé privée à partir à partir du mot de passe et une graine unique à chaque utilisateur donnée par le serveur.

Vincent F  [17 h 31]

Les pièces d'identité, tu les gardes que temporairement n'est-ce pas ? le temps de la vérification. Tu les supprimes après. Comme les banques, il redemande des pièces d'identité après x années.

Michaël Launay  [17 h 32]

Oui c'est prévu, mais comme c'est un parti politique ça vite craindre...

Michaël Launay [17 h 36]

t'as pas déjà eu ce genre de réflexions ? Après je pense faire cela uniquement en version 2, là on a décider de faire simple et vérifier les pièces en face cam ce qui oblige le vérificateur et le candidat à se synchroniser mais au moins y a rien qui circulent sur notre serveur ou notre messagerie (la mienne ![:clin_d'œil:](https://a.slack-edge.com/production-standard-emoji-assets/14.0/google-medium/1f609@2x.png) ).

Vincent F  [17 h 38]
Nan je fais pas de truc compliqué comme ça. Je fais juste du stockage encrypted at rest sur le serveur, et un accès restreint aux utilisateurs habilités via une api.

Michaël Launay  [17 h 38]

oki

Vincent F  [17 h 39]

Si tu veux vraiment que seul l'utilisateur ait la clé de déchiffrement, tu peux faire comme excalidraw, t'as la clé dans l'url

Vincent Fretin [17 h 40]

[https://blog.excalidraw.com/end-to-end-encryption/]

[End-to-End Encryption in the Browser | Excalidraw Blog](https://blog.excalidraw.com/end-to-end-encryption/)

Excalidraw is a whiteboard tool that lets you easily sketch diagrams that have a hand-drawn feel to them. It is very handy to dump your thoughts many of which are sensitive: designs for new features not yet released, interview questions, org charts, etc. (70 ko)

[https://blog.excalidraw.com/end-to-end-encryption/](https://blog.excalidraw.com/end-to-end-encryption/ "End-to-End Encryption in the Browser | Excalidraw Blog")

Michaël Launay  [17 h 40]

ah cool merci

Vincent F  [17 h 43]

Si tu t'inspires de ça, regarde vraiment le dernier code dans leur repository, il me semble qu'il avait modifié un truc ou deux depuis l'article.
```

Voir [End-to-End Encryption in the Browser | Excalidraw Blog](https://blog.excalidraw.com/end-to-end-encryption/)

# 2023-08-02

## Réflexion de Michaël Launay sur le chiffrage de bout en bout proposé

On utilise une enveloppe contenant la clé symétrique de chiffrement du document important comme la pièce d'identité.
Cette enveloppe sera dupliquée et chiffrée avec les clés publiques de chaque utilisateur de la plateforme concernés.
Ces enveloppes chiffrées asymétriquement ainsi que le document chiffré symétriquement seront stockés sur AlirPunkto.
La paire de clés (privée et publique) de chaque utilisateur est régénérée chaque fois que l'on en a besoin sur le navigateur de l'utilisateur à partir de son mot de passe qu'il est seul à connaître ET d'une graine fournie par AlirPunkto en début de procédure d'authentification, la clé privée n'est gardée sur le navigateur que le temps de la session.
La graine est unique pour chaque utilisateur, elle est le fruit du secret d'AlirPunkto pour les cookies, du numéro d'utilisateur et de la date (année, jour) de session qui correspondra à la date de création du document et sera donc un attribut (Cette graine est donc unique par jour et par utilisateur). 
Il y a autant d'enveloppes de créées sur le poste de l'utilisateur que de personnes devant voir le document.
Consulter un document revient donc pour AlirPunkto à régénérer la graine, à l'envoyer avec le document à déchiffrer et l'enveloppe de scellement correspondant à l'utilisateur.
Au navigateur de demander le mot de passe de l'utilisateur, puis de concaténer la graine, de générer les clés publique et privée, puis de déchiffrer le document avec la clé privée générée. Puis, en fin de session, d'oublier les clés.
La date de création d'un enregistrement de document est la date de début de procédure (gestion du passage d'un jour à l'autre).

## Avis de ChatGPT4

L'approche que vous avez décrite est ingénieuse et a le potentiel d'offrir un haut degré de sécurité. Le fait d'utiliser une clé symétrique pour chiffrer le document et ensuite chiffrer cette clé avec les clés publiques de chaque utilisateur permet un contrôle fin de l'accès au document. La régénération de la paire de clés à partir d'une graine unique et du mot de passe de l'utilisateur ajoute une autre couche de sécurité.

Cependant, il y a des considérations importantes :

1. **Complexité** : Ce système est assez complexe, ce qui peut entraîner des erreurs de mise en œuvre ou de compréhension pour ceux qui devront le maintenir à l'avenir.
    
2. **Dépendance au mot de passe** : Comme la clé privée est générée à partir du mot de passe et de la graine, si un utilisateur oublie son mot de passe, il perd l'accès à tous les documents chiffrés avec ce mot de passe.
    
3. **Sécurité du navigateur** : Générer et gérer des clés sensibles dans le navigateur peut être risqué, surtout si l'utilisateur utilise un navigateur ou un ordinateur compromis.
    
4. **Performance** : Le chiffrement et le déchiffrement dans le navigateur peuvent être coûteux en termes de performance, surtout si les documents sont volumineux ou si l'utilisateur a un appareil plus ancien.
    
5. **Audit de sécurité** : Une telle solution doit être soigneusement analysée et testée par des experts en sécurité pour identifier les éventuelles vulnérabilités.
    

En somme, c'est une approche prometteuse mais qui nécessite une mise en œuvre et une gestion prudentes, ainsi qu'une évaluation approfondie par des experts en sécurité.

## Variantes :

Michaël Launay : Une variante amusante et que si on n'utilise qu'une seule enveloppe que l'on chiffre utilisateur après utilisateur, alors il faut que l'on ait la collaboration de tous les utilisateurs dans un ordre donné (ou pas selon l'algorithme) pour accéder à la clé symétrique et donc pouvoir déchiffrer le document.

Pour conclure à faire en V2 @TODO V2

# 2023-08-03

Mail de Michaël Launay à L Z :
```
J'ai discuté avec Vincent de ma proposition et j'ai creusé les pistes qu'il m'a données.

Pour faire court, cette architecture est testée par Excalidraw (un outil de dessin collaboratif open source)  [https://blog.excalidraw.com/end-to-end-encryption/](https://blog.excalidraw.com/end-to-end-encryption/)

Ils le font pour ne pas avoir à stocker les dessins réalisés en clair sur leurs serveurs, sans non plus avoir à connaître la clé.

Leur réflexion date de 2020, on est donc dans l'air du temps.

Je propose donc d'implémenter AlirPunkto sur le scénario tel que tu le souhaites dans un premier temps et lorsque nous aurons plus d'utilisateurs ou si je souhaite creuser l'affaire avant et que j'en ai le temps j'implémenterai de tels mécanismes.
```

Je modifie le scénario Candidature.

# 2023-08-04
J'ai totalement récris le scénario Candidature pour fusionner la vérification du mail avec le captcha que j'ai remplacé par une opération simple consistant  à résoudre une formule de la forme "(quatre + trois ) * (sept + cinq) + deux" (Multiplication de la somme de deux chiffres compris entre 2 et 9 écrits en toutes lettres additionnés d'un chiffre compris entre 1 et 9 en toutes lettres), il suffit d'avoir un dictionnaire de traduction pour toute les langues pour "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf".

# 2023-08-21
J'ai entièrement revu le code de `register.py`.
J'y ai ajouté une énumération pour les états des candidatures.
Dans `register`, je réalise un match sur les états de la candidature et je traite la requête différemment selon cet état.
Afin de reprendre la procédure à n'importe quel point, je suggère d'ajouter, en tant que paramètre de l'URL, l'OID chiffré de la candidature.
Pour chiffrer cet OID, je propose de le concaténer avec une graine générée aléatoirement et conservée dans l'objet Candidature. Le tout serait alors chiffré en utilisant le secret de l'application.

# 2023-08-28
Réécriture de Candidature.py
Utilisation d'énumérés pour les états, les types de candidatures, et les votes.

# 2023-08-29
Remplacement des chaînes de caractères des Enums par des ID i18n :

**Utilisation de Clés I18n** : Plutôt que de stocker les valeurs textuelles directement dans l'enum, j'utilise des clés d'internationalisation (I18n keys). Ces clés serviront de références pour les chaînes traduites. Exemple :

```python
from enum import Enum

class VoteOutcome(Enum):
	YES = "vote.outcome.yes"
	NO = "vote.outcome.no"
	ABSTAIN = "vote.outcome.abstain"
```

2023-08-30
Face au problème d'envoi de mail, j'ai ajouté l'option `file` pour enregistrer les logs d'envoi en mode `debug` dans un fichier.
```ini
[handlers]
keys = console, file

[logger_yourapp]
level = DEBUG
handlers = file
qualname = AlirPunkto
propagate = 0

[handler_file]
class = handlers.TimedRotatingFileHandler
args = ('var/log/alirpunkto.log', 'midnight', 1, 7)
level = DEBUG
formatter = generic
```

Les message ne partaient pas car ils sont encapsulé dans une transaction et ne parte que si la transaction est commitée 


## Deux types de retour sur les vues

Dans le code de ma vue 'register.py' il y a deux type de return : 
```python
return HTTPFound(location=request.route_url('success'))
return {'form': form.render(), 'candidature': candidature}
```

## monitored_candidatures

Pour pouvoir gérer les relances, j'ai ajouté au singleton Candidatures un attribut _monitored_candidatures et son getter.

## Utilisation de Fernet pour le chiffrement et déchiffrement des OID

L'algorithme Fernet est une méthode de chiffrement symétrique développée pour être simple, rapide et sécurisée, tout en fournissant une vérification d'intégrité pour détecter toute modification non autorisée des données chiffrées.

Le processus de chiffrement avec Fernet se déroule comme suit :

1. **Génération de la clé :** Une clé secrète aléatoire est générée. Cette clé est utilisée pour chiffrer et déchiffrer les données.

2. **Préparation du message :** Le message à chiffrer est converti en octets (binaire) si ce n'est pas déjà le cas.

3. **Création de l'objet Fernet :** En utilisant la clé secrète générée, un objet Fernet est créé. Cet objet encapsule les détails nécessaires pour effectuer le chiffrement et le déchiffrement.

4. **Chiffrement :** Le message est chiffré en utilisant l'objet Fernet. Le processus de chiffrement implique les étapes suivantes :
   - Un vecteur d'initialisation (IV) est généré de manière aléatoire.
   - Le message est chiffré à l'aide d'une combinaison de l'algorithme AES (Advanced Encryption Standard) en mode CBC (Cipher Block Chaining) et du mode de remplissage PKCS7.
   - Le message chiffré est ensuite authentifié en utilisant le HMAC (Hash-based Message Authentication Code) avec l'algorithme SHA-256. Le HMAC garantit l'intégrité des données en produisant un code d'authentification basé sur le contenu du message chiffré.

5. **Création du token :** Le vecteur d'initialisation, le message chiffré et le code HMAC sont combinés pour former un "token" unique qui contient toutes les informations nécessaires pour déchiffrer et vérifier l'intégrité du message.

6. **Stockage du token :** Le token résultant est généralement renvoyé à l'utilisateur ou stocké dans un fichier ou une base de données.

Le processus de déchiffrement suit essentiellement les mêmes étapes dans l'ordre inverse. L'objet Fernet est utilisé pour extraire le vecteur d'initialisation, puis déchiffrer le message en utilisant la clé secrète. Le code HMAC est recalculé à partir du message déchiffré et comparé au code HMAC d'origine pour vérifier que le message n'a pas été altéré.

## Modification du mécanisme de Secret des fichier .ini

Les secrets doivent être généré avec le script generate_secret.py

```bash
cd $ALIR_PUNKTO_PROJECT
python3 alirpunkto/generate_secret.py
```
Ce qui donne quelque chose comme
```
SECRET_KEY="guCg0fbfPn3iazG_X5Xwk4qG1Z94vDtE4BxkmJLb-gw=" 
```

# 2023-09-05  
Le passage du seed dans les URL des e-mails pose problème, car nous ne changeons l'état des candidatures qu'après l'envoi du mail. Il faut donc envoyer l'état attendu, et non le seed, dans la fonction de calcul du hash pour l'URL.

# 2023-09-06  
Retour en arrière : on conserve le seed, mais on utilise celui de l'état que l'on a quitté.  
Modifiez le code pour enregistrer dans les modifications de la candidature le tuple (date, état, seed) sous forme d'objets et non plus sous forme de texte. Ajoutez les fonctions permettant de parcourir l'historique et de décrire les transitions.

# 2023-09-07  
Il y a un problème profond avec l'état des candidatures.  
Si l'on effectue le changement d'état avant l'envoi des e-mails, et que celui-ci échoue, le candidat reste bloqué dans un état où il n'a pas reçu son e-mail.  
La solution la plus simple serait d'associer un état à l'envoi de l'e-mail et de relancer les e-mails non envoyés. Cela permettrait de valider les actions du candidat et de reprendre là où les choses n'ont pas bien fonctionné, sans avoir à solliciter à nouveau le candidat.  
La liste des modifications est actuellement inconsistante dans la classe "Candidature". Je vais donc procéder à l'homogénéisation de la liste des modifications en utilisant le module `inspect` pour enregistrer le nom de la fonction ayant modifié les variables membres de la candidature.
Pour des raisons de performance je n'ai pas utilisé le module `inspect` :
```python
import inspect

def _change_seed(self,
				function_name:str = None,
				previous_value:Any = None,
				new_value:Any = None):

"""Change the seed of the candidature and memorize candidature changes.
Args:
function_name: The name of the function that triggered the change.
previous_value: The previous value of the candidature property.
new_value: The new value of the candidature property.
"""
	current_frame = inspect.currentframe()
	function_name = function_name if function_name else current_frame.f_code.co_name
...
```
J'ai mis le nom des méthodes dans les appels.

J'ai supprimé tout le mécanisme de rollback, qui n'a plus de raison d'être avec l'ajout des états d'envoi de mail.

Dans "Candidature", je mémorise la date, l'état de l'envoi du mail (voir l'énumération "CandidatureEmailSendStatus"), et le nom de la procédure d'envoi de mail. Ce dernier doit permettre de rappeler la procédure de préparation et d'envoi du mail pour les relances et les erreurs (Un match voire l'usage de `inspect`).

# 2023-09-16
Le système de vérification par résolution d'équation pose deux problèmes : l'espace des possibles n'est pas suffisant, et la notion de parenthèse est compliqué pour certains.
Il a donc été décider de réaliser quatre opérations simples : un premier nombre aléatoire de 1 à 9 est multiplié par un deuxième nombre aléatoire de 1 à 9 le tout additionné d'un troisième nombre aléatoire de 1 à 9, chacune des opérations est numérotée de A à D et le résultat doit être reporté dans les champs appelés A à D.

# 2023-09-23
Pour un stockage sécurisé des mots de passe, nous utilisons `bcrypt` qui est l'une des méthodes les plus couramment recommandées, car elle prend en compte le salage et les hachages itératifs, rendant les attaques par force brute beaucoup plus difficiles.
Mise  en œuvre:

1. Tout d'abord, nous devons installer la bibliothèque `bcrypt` via pip:

```
pip install bcrypt
```

2. Voici un exemple de code pour hacher un mot de passe avec bcrypt:

```python
import bcrypt

def hash_password(password: str) -> bytes:
    # Générer un "sel" pour le hachage. Le "sel" est généré automatiquement.
    salt = bcrypt.gensalt()

    # Hasher le mot de passe avec le sel. Le hachage résultant contient également le sel.
    hashed_password = bcrypt.hashpw(password.encode(), salt)

    return hashed_password

def check_password(provided_password: str, stored_hash: bytes) -> bool:
    # Vérifier un mot de passe. Retourne True si le mot de passe correspond, sinon False.
    return bcrypt.checkpw(provided_password.encode(), stored_hash)

# Exemple d'utilisation:
password = "my_secure_password"
hashed_pw = hash_password(password)

# Vérifier un mot de passe :
is_valid = check_password("some_password_to_check", hashed_pw)
print(is_valid)
```

**Points clés:**

- `bcrypt.gensalt()` génère un nouveau "sel" pour chaque hachage. C'est crucial pour garantir que chaque hachage est unique, même pour des mots de passe identiques.
  
- Le "sel" est stocké avec le hachage, donc nous n'avons pas besoin de le stocker séparément. Lors de la vérification du mot de passe, le sel est extrait du hachage stocké et utilisé pour vérifier le mot de passe fourni.

- La fonction `bcrypt.checkpw()` est utilisée pour vérifier les mots de passe, garantissant que la méthode correcte est utilisée pour extraire le sel et vérifier le hachage.

Expliquons étape par étape :

1. **Hachage du mot de passe**:

    ```python
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode(), salt)
    ```

   - `gensalt()` génère un "sel" aléatoire. Un sel est une séquence aléatoire qui est combinée avec le mot de passe avant d'être hachée. Ceci est fait pour éviter les attaques par table de hachage précalculée (comme les attaques de table arc-en-ciel).
  
   - `hashpw(password.encode(), salt)` hache le mot de passe fourni (`password`) avec le sel généré. Le résultat est une chaîne de bytes qui contient à la fois le sel et le hachage du mot de passe. C'est pourquoi nous n'avons pas besoin de stocker le sel séparément: il est inclus dans le hachage produit.

2. **Vérification du mot de passe**:

    ```python
    return bcrypt.checkpw(provided_password.encode(), stored_hash)
    ```

   - Lors de la vérification, nous utilisons la fonction `checkpw()`. Nous lui fournissons le mot de passe saisi par l'utilisateur et le hachage stocké (qui a été stocké dans la base de données lors de la création ou de la modification du mot de passe).

   - La fonction `checkpw` extrait le sel du hachage stocké et utilise ce sel pour hacher le `provided_password`. Si le hachage résultant correspond au hachage stocké, cela signifie que le mot de passe fourni est correct.

Grâce à cette méthode, même si deux utilisateurs ont le même mot de passe, leurs hachages stockés seront différents en raison des sels différents utilisés. De plus, étant donné que le sel est intégré au hachage, nous n'avons pas besoin de le gérer ou de le stocker séparément.

`bcrypt` a été conçu pour le hachage des mots de passe, en étant intentionnellement lent et coûteux en termes de ressources, ce qui le rend difficile à attaquer en utilisant des attaques par force brute.

## Bogue i18n chamaleon

J'ai dans la template `home.pt` des `i18n:translate` qui contiennent des variables:
```zpt
<h1 i18n:translate="welcome_msg">Welcome to Alirpunkto, the centralized service for applications of ${site_name}.</h1>
```
Si on enlève le i18n:translate `${site_name}` site_name est bien remplacé par la valeur de la variable, mais sinon cela affiche :
```txt
Bienvenue sur Alirpunkto, le service centralisé pour les applications de ${site_name}.
```
Si
```po
msgid "welcome_msg"
msgstr "Bienvenue sur Alirpunkto, le service centralisé pour les applications de ${site_name}."
```
Et si je ne mets pas de `$` dans le msgid
```txt
Bienvenue sur Alirpunkto, le service centralisé pour les applications de {site_name}.
```
si
```po
msgid "welcome_msg"
msgstr "Bienvenue sur Alirpunkto, le service centralisé pour les applications de {site_name}."
```
Je n'ai pas trouvé comment faire en sorte que cela fonctionne, sauf à éclater avec des `spans`, mais c'est pas ce que je veux.
Mon code python de ma vue `home.py`
```python
@view_config(route_name='home', renderer='alirpunkto:templates/home.pt')
def home_view(request):
	...
    return {'logged_in': logged_in, 'site_name': site_name, 'user': user, 'applications': applications }
```

# 2023-09-24

Pour enrichir le schéma ldap, il faut obtenir un numéro d'entreprise unique dont le numéro s'obtient au prés de l'IANA.

Pour ajouter un nouvel attribut `CandidatureType` à notre fichier de schéma LDIF, nous devrons ajouter une nouvelle entrée `attributeTypes`. `CandidatureType` sera stocké comme une chaîne de caractères et utilisons la syntaxe `1.3.6.1.4.1.1466.115.121.1.15` qui est pour `DirectoryString`.

```ldif
attributeTypes: ( 1.3.6.1.4.1.OUR_OID_NUMBER.1
  NAME 'candidatureNumber'
  DESC 'Candidature Number for the user'
  EQUALITY numericStringMatch
  SYNTAX 1.3.6.1.4.1.1466.115.121.1.36
  SINGLE-VALUE )

attributeTypes: ( 1.3.6.1.4.1.OUR_OID_NUMBER.2
  NAME 'CandidatureType'
  DESC 'Type of Candidature for the user'
  EQUALITY caseIgnoreMatch
  SYNTAX 1.3.6.1.4.1.1466.115.121.1.15
  SINGLE-VALUE )
```

Notons que j'ai modifié le OID en `.2` pour `CandidatureType` pour le distinguer de `candidatureNumber` qui a `.1`. Chaque OID est unique !

Explication du fichier LDIF :

1. **attributeTypes**: Il définit un nouvel attribut pour le schéma LDAP. C'est une extension standard pour décrire les objets dans un annuaire LDAP.

2. **NAME**: Le nom de l'attribut tel qu'il apparaîtra dans les entrées LDAP.

3. **DESC**: Une brève description de ce que fait cet attribut.

4. **EQUALITY**: Cela détermine comment les valeurs de cet attribut seront comparées. Par exemple, `caseIgnoreMatch` est couramment utilisé pour les chaînes de caractères où la casse n'a pas d'importance.

5. **SYNTAX**: Ceci spécifie le type de données pour l'attribut. Par exemple, `1.3.6.1.4.1.1466.115.121.1.15` est pour une chaîne de caractères.

6. **SINGLE-VALUE**: Cela signifie que l'attribut ne peut avoir qu'une seule valeur. Si nous voulons que l'attribut puisse avoir plusieurs valeurs, il faudra omettre cette option.

N'oublions pas de remplacer `OUR_OID_NUMBER` par le nombre OID que nous avons obtenu pour notre organisation ou application. L'OID doit être unique à votre organisation pour éviter les conflits avec d'autres extensions de schéma.

## Comment avoir un OID unique
L'OID (Object Identifier) est une chaîne de nombres qui identifie de manière unique un type d'objet ou un attribut dans divers standards, dont LDAP. 

Pour une entreprise nous devons faire une demande 
2. **IANA Private Enterprise Numbers**: Si nous ne disposons pas d'un préfixe OID, une solution courante est d'utiliser notre Private Enterprise Number (PEN) attribué par l'Internet Assigned Numbers Authority (IANA). Vous pouvez demander un PEN gratuitement auprès de l'IANA. Une fois que vous avez un PEN, vous pouvez utiliser ce nombre comme base pour vos OIDs en ajoutant vos propres sous-identifiants. Par exemple, si votre PEN est `12345`, vous pourriez avoir des OIDs comme `1.3.6.1.4.1.77777.1`, `1.3.6.1.4.1.77777.2`, etc.

   - Pour demander un PEN, allons sur le [site de l'IANA](https://www.iana.org/assignments/enterprise-numbers/).

3. **Générer un OID temporaire**: Si nous développons uniquement pour des tests internes et n'avons pas l'intention de publier ou de partager notre schéma, nous pourrions utiliser un OID généré de manière arbitraire. Cependant, c'est risqué pour la production ou pour des environnements où le schéma pourrait être partagé, car il pourrait y avoir des collisions.

4. **Registres nationaux**: Certains pays ont des registres nationaux où vous pouvez demander un OID. Cependant, les processus et la disponibilité peuvent varier.

Il est recommandé d'obtenir un OID officiel si nous prévoyons de déployer notre schéma dans un environnement de production ou de le partager avec d'autres.

Je vais le faire au nom de Logikascium.

# 2023-09-25

J'ai demandé un PEN pour Logikascium.
En attendant j'utilise le PEN 77777 qui n'est pas attribué
Par exemple
```ldif
attributeTypes: ( 1.3.6.1.4.1.77777.1
  NAME 'candidatureNumber'
  DESC 'Candidature Number for the user'
  EQUALITY numericStringMatch
  SYNTAX 1.3.6.1.4.1.1466.115.121.1.36
  SINGLE-VALUE )
```
Les numéros indiqués sont des Object Identifiers (OIDs), qui sont définis dans plusieurs normes et RFCs.

## 1.3.6.1.4.1
   - `1.3.6.1.4.1` est le préfixe d'OID pour les Private Enterprise Numbers, qui sont attribués par l'Internet Assigned Numbers Authority (IANA). Ce préfixe est défini dans la [RFC 1155](https://datatracker.ietf.org/doc/html/rfc1155), qui spécifie la structure de management information (SMI).

## 1.3.6.1.4.1.1466.115.121.1.36
   - Cet OID est lié à la syntaxe des attributs LDAP, et est défini dans la [RFC 4517](https://datatracker.ietf.org/doc/html/rfc4517), qui est une partie des normes LDAPv3. La partie `1.3.6.1.4.1.1466.115.121.1` est le préfixe pour les syntaxes d'attributs LDAP, et `36` est l'identifiant pour la syntaxe de chaîne numérique (`Numeric String`).

Pour travailler avec des schémas LDAP et pour comprendre les détails des OIDs utilisés, la RFC 4517 (et les autres RFCs liées à LDAPv3, comme la [RFC 4519](https://datatracker.ietf.org/doc/html/rfc4519) qui définit des types d'attributs standards) sera une lecture utile.

## Résolution des variables i18n

Pour pouvoir traduire des chaînes contenant des variables il faut utiliser `118n:name`, exemple :
```tal
<h1 i18n:translate="welcome_msg">Welcome to Alirpunkto, the centralized service for applications of <tal:var i18n:name="site_name">${site_name}</tal:var>.</h1>
```
Et `${site_name}` dans le msgstr pour le msgid
```pot

```

# 2023-09-26
# Traduction de la doc i18nmessageid
[i18nmessageid](https://zopei18nmessageid.readthedocs.io/en/latest/narr.html#example-usage)
Utilisation de zope.i18nmessageid
## Justification

Pour traduire n'importe quel texte, nous devons être capables de découvrir le domaine source du texte. Un domaine source est un identifiant qui identifie un projet produisant des chaînes de caractères sources de programme. Les chaînes sources se trouvent sous forme de littéraux dans les programmes Python, de texte dans les templates, et de certains textes dans les données XML. Le projet implique une langue source et un contexte d'application.
Messages et Domaines

On peut considérer un domaine source comme une collection de messages et de chaînes de traduction associées. Le domaine aide à lever l'ambiguïté des messages en fonction du contexte : par exemple, le message dont la chaîne source est "draw" signifie une chose dans un jeu de tir à la première personne, et une autre dans un logiciel graphique : dans le premier cas, le domaine du message pourrait être "ok_corral", tandis que dans le second, il pourrait être "gimp".

Nous devons souvent créer des chaînes unicode qui seront affichées par des vues séparées. La vue ne peut pas traduire la chaîne sans connaître son domaine source. Un littéral de chaîne ou unicode ne contient pas d'informations de domaine, donc nous utilisons des instances de la classe Message. Les messages sont des chaînes unicode qui portent un domaine source de traduction et éventuellement une traduction par défaut.
Factories de Messages

Les messages sont créés par une factory de messages appartenant à un domaine de traduction donné. Chaque factory de messages est créée en instanciant une MessageFactory, en passant le domaine correspondant au projet qui gère les traductions correspondantes.

```python

>>> from zope.i18nmessageid import MessageFactory
>>> factory = MessageFactory('monprojet')
>>> foo = factory('foo')
>>> foo.domain
'monprojet'
```

Le projet Zope utilise le domaine "zope" pour ses messages. Ce package exporte une factory déjà créée pour ce domaine :
```python
>>> from zope.i18nmessageid import ZopeMessageFactory as _z_
>>> foo = _z_('foo')
>>> foo.domain
'zope'
```

Exemple d'utilisation

Dans cet exemple, nous créons une factory de messages et l'assignons à _. Par convention, nous utilisons _ comme nom de notre factory pour être compatible avec les outils d'extraction de chaînes traduisibles comme xgettext. Nous appelons ensuite _ avec une chaîne qui doit être traduisible :

```python
>>> from zope.i18nmessageid import MessageFactory, Message
>>> _ = MessageFactory("futurama")
>>> robot = _(u"message-robot", u"${name} est un robot.")
```
Les messages semblent d'abord être des chaînes unicode :

```python
>>> robot == u'message-robot'
True
>>> isinstance(robot, unicode)
True
```

Les informations supplémentaires de domaine, par défaut et de mappage sont disponibles via des attributs :

```python
>>> robot.default == u'${name} est un robot.'
True
>>> robot.mapping
>>> robot.domain
'futurama'
```
Les attributs du message sont considérés comme faisant partie de l'objet message immuable. Ils ne peuvent pas être modifiés une fois l'id du message créé :
```python
>>> robot.domain = "planetexpress"
Traceback (most recent call last):
...
TypeError: attribut en lecture seule

>>> robot.default = u"${name} n'est pas un robot."
Traceback (most recent call last):
...
TypeError: attribut en lecture seule

>>> robot.mapping = {u'name': u'Bender'}
Traceback (most recent call last):
...
TypeError: attribut en lecture seule
```

Si vous devez changer leurs informations, vous devrez créer un nouvel id de message :

```python
>>> new_robot = Message(robot, mapping={u'name': u'Bender'})
>>> new_robot == u'message-robot'
True
>>> new_robot.domain
'futurama'
>>> new_robot.default == u'${name} est un robot.'
True
>>> new_robot.mapping == {u'name': u'Bender'}
True

Enfin, les messages sont réductibles pour le pickling :

>>> callable, args = new_robot.__reduce__()
>>> callable is Message
True
>>> args == (u'message-robot',
...          'futurama',
...          u'${name} est un robot.',
...          {u'name': u'Bender'})
True

>>> fembot = Message(u'fembot')
>>> callable, args = fembot.__reduce__()
>>> callable is Message
True
>>> args == (u'fembot', None, None, None)
True
```
Le pickling et l'unpickling fonctionnent, ce qui signifie que nous pouvons stocker les IDs de message dans une base de données :

```python
>>> from pickle import dumps, loads
>>> pystate = dumps(new_robot)
>>> pickle_bot = loads(pystate)
>>> (pickle_bot,
...  pickle_bot.domain,
...
```

# 2023-10-04

La fonction `_` renvoyée par `TranslationStringFactory` est une fonction qui crée des instances de `TranslationString`, qui doivent ensuite être traduites par un `Localizer`. Le `Localizer` utilise la langue de la requête pour déterminer la traduction correcte à utiliser.

Quand nous faisons `_("welcome")`, cela crée une instance de `TranslationString`, qui n'est pas automatiquement traduite en chaîne de caractères. Nous devons utiliser un `Localizer` pour obtenir la traduction réelle. C'est pourquoi lorsque nous faisons `localizer.translate(_("welcome"))`, nous obtenons la traduction correcte.

Ainsi :
```python
>>> from pyramid.i18n import get_localizer, TranslationStringFactory
>>> _ = TranslationStringFactory("alirpunkto")
>>> _
<function TranslationStringFactory.<locals>.create at 0x7fcb8f3a7640>  
>>> _("welcome")  
'welcome'  
>>> # Mais il faut faire
>>> localizer = get_localizer(request)  
>>> localizer.translate(_("welcome"))  
'Bienvenue'
```

# 2023-10-18

Traduction en français de [Deform Internationalization](https://docs.pylonsproject.org/projects/deform/en/latest/i18n.htm)l
En suivant le mécanisme de d'initialisation de la traduction les formulaires ont été traduit :
## Internationalisation des schema deform
Deform est entièrement internationalisable et localisable. Des fichiers gettext .mo existent dans les paquets deform et colander qui contiennent des traductions (actuellement incomplètes) vers différentes langues dans le but d'afficher des messages d'erreur localisés.

Voici comment commencer avec l'internationalisation (i18n) dans Pyramid :

python

```python
import deform
from pkg_resources
import resource_filename
from pyramid.i18n
import get_localizer
from pyramid.threadlocal
import get_current_request

def main(global_config, **settings):
	config = Configurator(settings=settings)
	config.add_translation_dirs(
	    'colander:locale',
	    'deform:locale',
	)

def traducteur(term):
	return get_localizer(get_current_request()).translate(term)     
	chemin_template_deform = resource_filename('deform', 'templates/')     
	zpt_renderer = deform.ZPTRendererFactory(
	    [chemin_template_deform],
	    translator=traducteur,
	)
	deform.Form.set_default_renderer(zpt_renderer)
```

Consultez la démo d'internationalisation pour voir comment les messages d'erreur et de statut de Deform peuvent être localisés. Cette démonstration utilise les fonctionnalités d'internationalisation et de localisation de Pyramid pour afficher les messages d'erreur Deform dans les rendus de formulaire Chameleon.

**Explication** :

Deform est un outil qui peut être utilisé avec l'internationalisation, ce qui signifie qu'il peut s'adapter à différentes langues et régions. En particulier, il a des fichiers `.mo` qui permettent de traduire des messages d'erreur dans différentes langues, bien que ces traductions ne soient pas encore complètes.

Le code donné est un exemple de la manière dont vous pourriez configurer l'internationalisation dans une application Pyramid qui utilise Deform.

1. On importe les modules nécessaires.
2. Dans la fonction `main`, on configure Pyramid pour utiliser les répertoires de traduction fournis par `deform` et `colander`.
3. On définit une fonction `traducteur` qui prend un terme et renvoie sa traduction. Cette fonction utilise le localiseur de Pyramid pour obtenir la traduction.
4. On définit où Deform peut trouver ses templates et on configure Deform pour utiliser notre fonction `traducteur` lors de la génération de ses rendus.
5. Enfin, on configure Deform pour utiliser un rendu spécifique par défaut.

La démo mentionnée à la fin est probablement un exemple concret montrant comment ces messages d'erreur traduits apparaissent dans une application réelle.

# 2023-10-19
@TODO supprimer de l'historique des candidatures les mots de passe lors du set data !!!!
@TODO Utiliser aussi des schemas DeForm pour :
- la saisie de l'adresse mail,
- du challenge,

Utilisation du schéma pour la saisie du pseudo, du mot de passe et confirmation du mot de passe pour les membres ordinaires.
Y ajouter les validateurs.
Là il y a une faiblesse sur les contrôles des saisies.

# 2023-10-23

L'erreur LDAP venait de l'obligation de fournir `sn`
Pour déboguer, j'ai mis un point d'arrêt sur le `add` d'une entrée ldap en python, puis j'ai exécuté :
```python
print(conn.last_error)
```
et j'ai obtenu:
```
(Pdb) print(conn.last_error)
objectClassViolation
```

Explication de chat GPT
```
Les attributs que j'ai fournis à ldap semblent corrects pour une entrée utilisant la classe d'objet `inetOrgPerson`. Cependant, l'erreur `objectClassViolation` indique toujours une incohérence avec le schéma LDAP.

En examinant les attributs que vous avez fournis, quelques points à vérifier :

1. **Attribut `sn` manquant** : La classe d'objet `inetOrgPerson` nécessite généralement que vous fournissiez un attribut `sn` (pour "surname" ou "nom de famille"). C'est souvent un attribut obligatoire. Vous devez ajouter cet attribut à votre dictionnaire d'attributs.

2. **Vérifier les autres attributs** :
    - Assurez-vous que l'attribut `uid` est unique dans votre LDAP pour la branche ou la base DN que vous ciblez.
    - Assurez-vous que l'attribut `userPassword` est bien encodé. Dans certaines configurations LDAP, vous devez utiliser une méthode spécifique pour encoder le mot de passe. Par exemple, vous pourriez avoir besoin de le hacher en utilisant SHA ou SSHA.

3. **Chemin complet de DN** : Assurez-vous que le DN que vous créez est correct et que la base DN (`LDAP_BASE_DN`) et l'unité organisationnelle (`LDAP_OU`) existent bien dans l'annuaire LDAP. Vous semblez avoir ajouté une logique pour gérer le cas où `LDAP_OU` pourrait être nul, mais assurez-vous que la valeur de `dn` est correcte et valide pour votre LDAP.

4. **Autres classes d'objet ou attributs** : Assurez-vous qu'il n'y a pas d'autres exigences pour votre configuration spécifique d'OpenLDAP qui nécessiteraient une autre classe d'objet ou un autre attribut à être fourni.

5. **Logs OpenLDAP** : Vous pouvez également consulter les logs du serveur OpenLDAP lui-même. Si le serveur est configuré pour enregistrer des informations détaillées, il pourrait y avoir plus d'informations sur pourquoi l'ajout a échoué.

Je vous suggère de commencer par ajouter l'attribut `sn` à votre dictionnaire d'attributs et de réessayer. Si cela ne résout pas le problème, passez aux autres étapes de dépannage.
```

# 2023-12-02

Les problèmes suivants ont été identifiés dans l'application AlirPunkto qui demande d'améliorer l'architecture:

## Problème 1: Perte de Connexion avec le Serveur de Mail
C.f Issue #46

**Situation Actuelle**:
- Lors des tests, si la connexion avec le serveur de mail est perdue, le changement d'état de la candidature est effectué sans que l'utilisateur ne reçoive de mail.
- Ce problème affecte le processus de vérification de l'humanité de l'utilisateur (le défi mathématique).

**Solution Proposée**:
1. **Gestion des Exceptions**: Mettre en place une gestion robuste des exceptions pour la fonction d'envoi de mail. Si l'envoi échoue, l'exception doit être capturée.
2. **Renvoi**: En cas d'échec, programmer des tentatives répétées d'envoi du mail à intervalles réguliers.
3. **Confirmation de l'État de la Candidature**: Changer l'état de la candidature, mais indiquer le problème au candidat en l'invitant à de revenir plus tard et de recommencer la procédure ce qui déclenchera un nouvel envoi du dernier mail.
4. **Feedback Utilisateur**: Informer l'utilisateur sur le portail de l'échec de l'envoi du mail et de la tentative de renvoi.

### Problème 2: Recréation d'une Candidature Existante
C.f Issue #47

**Situation Actuelle**:
- Si une candidature existante est recréée, l'utilisateur est redirigé directement vers l'état correspondant, ce qui représente une faille de sécurité.

**Solution Proposée**:
1. **Vérification de l'Unicité**: Avant de créer une nouvelle candidature, vérifier si une candidature similaire existe déjà.
2. **Redirection Sécurisée**: Si une candidature existante est détectée, ne pas rediriger directement l'utilisateur. Au lieu de cela, renvoyer le dernier mail et demander de suivre le lien mis dans le mail.
3. **Message d'information**: Fournir un message explicite indiquant pourquoi la création de la candidature n'est pas permise.

## Solution pour les Mails

- Mettre en place un système de file d'attente pour les mails. Cela permet de réessayer l'envoi des mails en cas d'échec initial.
- Si un utilisateur cherche à recréer une candidature déjà existante qui ne soit pas à l'état  APPROVED ou REJECTED, alors lui renvoyer le dernier mail avec le lien à suivre pour reprendre là où il s'est arrêté, prévenir sur le portail qu'il doit suivre le lien qu'il contient.

### Implémentation Technique

1. **File d'Attente de Mail**: Voir si l'on doit utiliser une bibliothèque de file d'attente comme `RQ` (Redis Queue) pour gérer les tentatives d'envoi de mail.

## Problème 3 
C.f issue #48

Le test d'unicité des mails ne fonctionne que partiellement, car elle n'est vérifiée que dans ldap et non pas aussi dans les candidatures en cours.

# 2024-01-05
Voici la notice d'ajout du schéma ldap alirpunkto_schema.ldif
Voici un exemple de documentation à inclure dans le fichier `README.md` de votre projet AlirPunkto pour expliquer comment ajouter le schéma `alirpunkto/alirpunkto_schema.ldif` à un serveur OpenLDAP sur Ubuntu 22.04 :

## Ajout du Schéma AlirPunkto à OpenLDAP sous Ubuntu 22.04

Cette section vous guide à travers les étapes nécessaires pour intégrer le schéma personnalisé `alirpunkto_schema.ldif` dans un serveur OpenLDAP sur Ubuntu 22.04.

### Prérequis

- Un serveur OpenLDAP installé sur Ubuntu 22.04.
- Des droits d'administrateur sur le serveur LDAP.
- Le fichier `alirpunkto_schema.ldif` disponible dans le répertoire `alirpunkto` de ce projet.

### Étapes d'Installation

1. **Connexion au Serveur**  
   Connectez-vous à votre serveur Ubuntu où OpenLDAP est installé.

2. **Arrêt du Service LDAP**  
   Avant de modifier la configuration, arrêtez le service LDAP pour éviter toute corruption de données.
   ```bash
   sudo systemctl stop slapd
   ```

3. **Localisation du Fichier Schema**  
   Assurez-vous que le fichier `alirpunkto_schema.ldif` est présent sur le serveur. S'il ne l'est pas, transférez-le dans un répertoire approprié (par exemple, `/tmp`).

4. **Ajout du Schéma au Serveur LDAP**  
   Exécutez la commande suivante pour ajouter le schéma à votre annuaire LDAP :
   ```bash
   sudo ldapadd -Y EXTERNAL -H ldapi:/// -f /chemin/vers/alirpunkto_schema.ldif
   ```
   Remplacez `/chemin/vers/alirpunkto_schema.ldif` par le chemin réel du fichier `alirpunkto_schema.ldif` sur votre serveur.

5. **Redémarrage du Service LDAP**  
   Après l'ajout réussi du schéma, redémarrez le service LDAP :
   ```bash
   sudo systemctl start slapd
   ```

6. **Vérification**  
   Vérifiez que le schéma a été ajouté correctement. Vous pouvez le faire en consultant les journaux d'OpenLDAP ou en utilisant un outil LDAP pour explorer la configuration du schéma.

### Dépannage

Si vous rencontrez des problèmes lors de l'ajout du schéma, consultez les journaux d'OpenLDAP pour des informations détaillées sur les erreurs. Les journaux peuvent souvent fournir des indices utiles sur ce qui a pu mal tourner.

### Notes Importantes

- Assurez-vous de faire une sauvegarde de la configuration LDAP existante avant d'effectuer des modifications.
- Toute modification de la configuration LDAP doit être effectuée avec prudence, car des erreurs peuvent affecter la stabilité et la sécurité du service.
- Testez les modifications dans un environnement de développement avant de les appliquer sur un serveur de production.

# 2024-01-06

La description de olcObjectClasses pour ajouté un schéma à ldap nécessite des `$` comme séparateur des champs :
```ldif
olcObjectClasses: ( 1.3.6.1.4.1.61000.2.2.1
  NAME 'alirpunktoPerson' 
    DESC 'AlirPunkto specific person object class' 
  SUP inetOrgPerson 
  STRUCTURAL 
    MUST (
      uid $ cn $ mail $ employeeType $ isActive $ isOrdinaryMember $
      isCooperatorMember $ isBoardMember $
      isMemberOfMediationArbitrationCouncil )
    MAY (
      sn $ gn $ nationality $ birthdate $ preferredLanguage $
      secondLanguage $ thirdLanguage $ cooperativeBehaviourMark $
      lastUpdateBehaviour $ userProfileText $ userProfileImage $
      thirdLanguage )
  )
```

L'ajout se fait alors :
```bash
sudo -i
apt install schema2ldif
ldap-schema-manager -i /home/michaellaunay/workspace/alirpunkto/alirpunkto/alirpunkto_schema.ldif
ldap-schema-manager -m /home/michaellaunay/workspace/alirpunkto/alirpunkto/alirpunkto_schema.ldif -n
```
Paradoxalement la premier appel ldap-schema-manager -i ne signale pas les erreurs et sort en 0, alors que la mise à jour faite par le second appel indiquait une erreur 80 qui correspondait à l'abscence de `$`

# 2024-01-08

La façon dont est gérée l'admin d'openldap ne permet pas de gérer correctement l'administration d'Alirpunkto, car il n'a pas forcément d'entrée dans ldap. En conséquence, j'ai ajouté le compte ADMIN d'arlipunkto dont le login, le mail et le mot de passe sont définis dans le .env.

# 2024-01-27

Ajout d'une vue permettant de rendre une zpt et de la traduire selon la locale de l'utilisateur, puis de la retourner sous forme de texte.

# 2024-01-28

Remplacement de la vue get_email par un passage de variable, attention nous sommes limité à la taille limite d'une url soit 4096 octets (2096 pour les vielles version de IE)

# 2024-01-31

Voici le scénario de réinitialisation du mot de passe :

    - 1) AlirPunkto affiche la zpt forgot_password.pt de saisie du mail
    - 2) L'utilisateur saisit son mail et valide
    - 3) AlirPunkto vérifie que le mail existe dans ldap
    - 3.1) Si le mail n'existe pas, AlirPunkto affiche un message indiquant que si l'utilisateur existe, il recevra un mail 
    - 3.2) Fin de la procédure
    - 4) AlirPunkto récupère les informations concernant l'utilisateur depuis le ldap
    - 5) AlirPunkto regarde s'il existe une candidature pour l'utilisateur
    - 5.1) Si non, AlirPunkto crée une candidature à partir des informations du ldap
    - 5.2) Si oui, AlirPunkto récupère la candidature et la met à jour avec les informations du ldap (priorité au ldap)
    - 6) AlirPunkto génère un token hashé de réinitialisation du mot de passe
    - 7) AlirPunkto crée un événement de réinitialisation du mot de passe et lui ajoute le token
    - 8) AlirPunkto crée un lien vers la candidature avec le token
    - 9) AlirPunkto envoie un mail à l'utilisateur avec le lien
    - 10) AlirPunkto affiche un message indiquant que le mail a été envoyé (même message que 3.1)
    - 11) L'utilisateur reçoit le mail et clique sur le lien
    - 11.1) Si le lien est invalide ou expiré, AlirPunkto affiche un message d'erreur
    - 11.2) Retour en 1
    - 12) AlirPunkto affiche la zpt forgot_password.pt de saisie du nouveau mot de passe
    - 13) L'utilisateur saisit son nouveau mot de passe et valide
    - 14) AlirPunkto vérifie que le mot de passe est valide et respecte les contraintes de sécurité
    - 14.1) Si le mot de passe n'est pas valide, AlirPunkto affiche un message d'erreur
    - 14.2) Retour en 12
    - 15) AlirPunkto met à jour le mot de passe dans le ldap
    - 16) AlirPunkto met à jour les événements de la candidature
    - 17) AlirPunkto affiche la zpt forgot_password.pt de confirmation de changement de mot de passe
    - 18) AlirPunkto envoie un mail à l'utilisateur pour le prévenir du changement de mot de passe