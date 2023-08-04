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
