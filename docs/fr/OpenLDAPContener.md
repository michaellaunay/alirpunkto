# Configuration et Utilisation du Conteneur OpenLDAP

Ce guide explique comment construire et exécuter le conteneur Docker pour OpenLDAP avec support pour le schéma Alirpunkto.

## Préparation

### 1. Structure des Fichiers

Créons un répertoire pour notre projet et placons-y les fichiers suivants :

```
ldap-docker/
├── Dockerfile            # Le Dockerfile fourni
├── start_ldap.sh         # Le script de démarrage fourni
└── schema/               # Répertoire pour les schémas LDAP personnalisés
    └── alirpunkto_schema.ldif  # Notre schéma Alirpunkto
```

### 2. Copie du Schéma Alirpunkto

Copions notre fichier `alirpunkto_schema.ldif` dans le répertoire `schema/`.

## Construction de l'Image

Exécutons la commande suivante pour construire l'image Docker :

```bash
docker build -t alirpunkto-ldap .
```

## Exécution du Conteneur

### Option 1 : Nouvelle Installation avec Configuration Automatique

Pour démarrer un nouveau serveur LDAP avec une configuration par défaut :

```bash
docker run -d \
  --name alirpunkto-ldap \
  -p 389:389 \
  -p 636:636 \
  -e LDAP_ADMIN_PASSWORD=notre_mot_de_passe_admin \
  -v $(pwd)/schema:/etc/ldap/schema \
  alirpunkto-ldap
```

### Option 2 : Utilisation d'une Configuration LDAP Existante

Pour utiliser une configuration LDAP existante depuis notre système hôte :

```bash
docker run -d \
  --name alirpunkto-ldap \
  -p 389:389 \
  -p 636:636 \
  -v /etc/ldap:/etc/ldap \
  -v /var/lib/ldap:/var/lib/ldap \
  alirpunkto-ldap
```

### Option 3 : Volume Persistant pour les Données

Pour conserver les données LDAP entre les redémarrages du conteneur :

```bash
docker run -d \
  --name alirpunkto-ldap \
  -p 389:389 \
  -p 636:636 \
  -e LDAP_ADMIN_PASSWORD=notre_mot_de_passe_admin \
  -v ldap-config:/etc/ldap \
  -v ldap-data:/var/lib/ldap \
  -v $(pwd)/schema:/etc/ldap/schema \
  alirpunkto-ldap
```

## Utilisation de ldapvi

Une fois le conteneur en cours d'exécution, nous pouvons utiliser ldapvi pour interagir avec le serveur LDAP :

```bash
docker exec -it alirpunkto-ldap ldapvi -h localhost -D "cn=admin,dc=alirpunkto,dc=com" -w notre_mot_de_passe_admin -b "dc=alirpunkto,dc=com"
```

## Vérification de l'Installation

Pour vérifier que le serveur LDAP fonctionne correctement :

```bash
docker exec -it alirpunkto-ldap ldapsearch -x -h localhost -b "dc=alirpunkto,dc=com" -D "cn=admin,dc=alirpunkto,dc=com" -w notre_mot_de_passe_admin
```

## Scripts d'Initialisation Personnalisés

Nous pouvons ajouter des scripts d'initialisation personnalisés qui seront exécutés lors du premier démarrage :

1. Créons un répertoire `init` dans notre projet
2. Ajoutons nos scripts `.sh` ou fichiers `.ldif` dans ce répertoire
3. Montons ce répertoire lors du démarrage du conteneur :

```bash
docker run -d \
  --name alirpunkto-ldap \
  -p 389:389 \
  -p 636:636 \
  -v $(pwd)/init:/docker-entrypoint-initdb.d \
  -v $(pwd)/schema:/etc/ldap/schema \
  alirpunkto-ldap
```

## Exemple de Fichier LDIF pour Ajouter un Utilisateur Alirpunkto

Voici un exemple de fichier LDIF pour ajouter un utilisateur utilisant le schéma Alirpunkto.
Créons un fichier `init/add_user.ldif` :

```ldif
dn: ou=users,dc=alirpunkto,dc=com
objectClass: organizationalUnit
ou: users

dn: cn=johndoe,ou=users,dc=alirpunkto,dc=com
objectClass: top
objectClass: inetOrgPerson
objectClass: alirpunktoPerson
cn: johndoe
sn: Doe
uid: 12345
givenName: John
mail: john.doe@example.com
employeeType: CONTRIBUTOR
isActive: TRUE
nationality: French
birthdate: 1990-01-01
preferredLanguage: fr
secondLanguage: en
```

Nous pouvons l'importer en montant le répertoire init :

```bash
docker run -d \
  --name alirpunkto-ldap \
  -p 389:389 \
  -p 636:636 \
  -e LDAP_ADMIN_PASSWORD=notre_mot_de_passe_admin \
  -v $(pwd)/init:/docker-entrypoint-initdb.d \
  -v $(pwd)/schema:/etc/ldap/schema \
  alirpunkto-ldap
```

## Accès aux Logs

Pour voir les logs du conteneur :

```bash
docker logs alirpunkto-ldap
```

## Troubleshooting

Si nous rencontrons des problèmes avec l'importation du schéma, nous pouvons nous connecter au conteneur et effectuer l'importation manuellement :

```bash
docker exec -it alirpunkto-ldap bash

# Dans le conteneur
ldap-schema-manager -i /etc/ldap/schema/alirpunkto_schema.ldif
ldap-schema-manager -m /etc/ldap/schema/alirpunkto_schema.ldif -n
```