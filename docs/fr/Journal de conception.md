2023-07-22
Le fonctionnement par simple candidature sans vérification du mail avant soumission est une faille dans le sens où les électeur peuvent ainsi être soumis à des candidatures qui sont des spams.
Pour éviter cela il faut modifier la conception de la vue `register.py` pour ajouter dans le scnério de candidature l'envoi du mail de confirlation de candidature. [[Candidature]]

@TODO
Ajouter le scheduler voir [pyramid_scheduler](https://pypi.org/project/pyramid_scheduler/) ou https://stackoverflow.com/questions/28584597/python-pyramid-periodic-task

@TODO
Check le markdown des docs