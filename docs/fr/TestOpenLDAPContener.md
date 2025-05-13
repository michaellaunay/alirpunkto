# Guide: LDAP Container for Unit Testing

Ce guide explique comment utiliser le conteneur LDAP pour les tests unitaires de notre application Alirpunkto.

## Structure du Projet

Voici la structure de fichiers recommandée pour notre environnement de test LDAP :

```
ldap-test/
├── Dockerfile.test                # Dockerfile spécifique pour les tests
├── docker-compose.test.yml        # Configuration docker-compose pour les tests
├── run_ldap_tests.sh              # Script pour exécuter les tests
├── start_test_ldap.sh             # Script de démarrage du conteneur de test
├── schema/
│   └── alirpunkto_schema.ldif     # notre schéma Alirpunkto
└── test-data/
    └── test-data.ldif             # Données de test LDIF
```

## 1. Configuration des Fichiers de Test

### Préparation des Données de Test

1. Placons notre fichier `alirpunkto_schema.ldif` dans le répertoire `schema/`.

2. Créons un fichier `test-data.ldif` dans le répertoire `test-data/` avec des exemples d'utilisateurs et de groupes pour nos tests :
   - Incluons différents types d'utilisateurs (ORDINARY, CONTRIBUTOR)
   - Créons quelques groupes avec des membres
   - Assurons-nous de couvrir tous les attributs que nous souhaitons tester

## 2. Utilisation du Conteneur de Test

### Démarrage Rapide

Pour lancer le conteneur de test LDAP :

```bash
docker-compose -f docker-compose.test.yml up -d
```

Pour exécuter les tests avec le conteneur LDAP :

```bash
./run_ldap_tests.sh
```

### Options Avancées

#### Modification du Port

Par défaut, le conteneur LDAP de test utilise le port 3389 pour éviter les conflits. Nous pouvons modifier ce port dans le fichier `docker-compose.test.yml`.

#### Mot de Passe Administrateur

Nous pouvons spécifier un mot de passe administrateur fixe :

```bash
LDAP_ADMIN_PASSWORD=notre_mot_de_passe docker-compose -f docker-compose.test.yml up -d
```

Ou laisser le script en générer un aléatoire (recommandé pour l'intégration continue).

## 3. Intégration avec notre Application

### Configuration LDAP pour les Tests

Pour configurer notre application Alirpunkto pour qu'elle utilise le serveur LDAP de test :

1. Modifions les paramètres LDAP dans nos fichiers de configuration de test :
   ```ini
   ldap.uri = ldap://localhost:3389
   ldap.base_dn = dc=alirpunkto,dc=com
   ldap.admin_dn = cn=admin,dc=alirpunkto,dc=com
   ldap.admin_password = test_password  # ou récupérons-le dynamiquement
   ```

2. Dans notre code de test, utilisons les variables d'environnement définies par `run_ldap_tests.sh` :
   ```python
   ldap_host = os.environ.get('LDAP_HOST', 'localhost')
   ldap_port = os.environ.get('LDAP_PORT', '3389')
   ldap_admin_dn = os.environ.get('LDAP_ADMIN_DN')
   ldap_admin_password = os.environ.get('LDAP_ADMIN_PASSWORD')
   ```

## 4. Exemples de Tests LDAP

Voici des exemples de tests que nous pouvons effectuer :

### Tests d'Authentification

```python
def test_ldap_authentication(self):
    # Test avec identifiants valides
    self.assertTrue(authenticate_user("testuser1", "password"))
    
    # Test avec identifiants invalides
    self.assertFalse(authenticate_user("testuser1", "wrong_password"))
```

### Tests de Recherche

```python
def test_find_users_by_attribute(self):
    # Recherche d'utilisateurs par attribut
    users = find_users_by_attribute("employeeType", "CONTRIBUTOR")
    self.assertEqual(len(users), 1)
    self.assertEqual(users[0]['uid'], 'test002')
```

### Tests d'Attributs Spécifiques

```python
def test_alirpunkto_specific_attributes(self):
    # Vérification des attributs spécifiques à Alirpunkto
    user = find_user_by_uid("test002")
    self.assertEqual(user['nationality'], 'German')
    self.assertEqual(float(user['cooperativeBehaviourMark']), 8.5)
```

## 5. Intégration Continue (CI/CD)

Pour intégrer ces tests dans notre pipeline CI/CD :

### GitHub Actions

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install python-ldap pytest
      - name: Run LDAP tests
        run: |
          chmod +x run_ldap_tests.sh
          ./run_ldap_tests.sh
```

### GitLab CI

```yaml
test:
  stage: test
  image: python:3.11
  services:
    - docker:dind
  variables:
    DOCKER_HOST: tcp://docker:2375
  before_script:
    - pip install python-ldap pytest
    - docker-compose -f docker-compose.test.yml up -d
  script:
    - ./run_ldap_tests.sh
```

## 6. Bonnes Pratiques

1. **Isolation**: Le conteneur de test doit être complètement isolé de notre environnement de production.

2. **Idempotence**: Les tests doivent pouvoir être exécutés plusieurs fois sans effets secondaires.

3. **Réinitialisation**: La base de données LDAP doit être réinitialisée à un état connu avant chaque série de tests.

4. **Parallélisation**: Pour exécuter des tests en parallèle, utilisons des ports LDAP différents pour chaque instance.

5. **Mots de passe**: Ne codons pas en dur les mots de passe dans nos tests. Utilisons des variables d'environnement.

## 7. Dépannage

### Problèmes de Connexion

Si nous ne pouvons pas nous connecter au serveur LDAP :

```bash
# Vérifions que le conteneur est en cours d'exécution
docker ps | grep ldap-test

# Vérifions les logs du conteneur
docker logs ldap-test

# Testons la connexion manuellement
ldapsearch -x -H ldap://localhost:3389 -b "dc=alirpunkto,dc=com" -D "cn=admin,dc=alirpunkto,dc=com" -w "test_password"
```

### Problèmes d'Importation de Schéma

Si le schéma Alirpunkto n'est pas correctement importé :

```bash
# Connectons-nous au conteneur
docker exec -it ldap-test bash

# Vérifions le schéma
ldapsearch -Y EXTERNAL -H ldapi:/// -b "cn=schema,cn=config" -s one "(cn=*alirpunkto*)"

# Importons le schéma manuellement
ldap-schema-manager -i /etc/ldap/schema/alirpunkto_schema.ldif
ldap-schema-manager -m /etc/ldap/schema/alirpunkto_schema.ldif -n
```