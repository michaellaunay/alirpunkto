# alirpunkto
Alirpunkto (Access Point in Esperanto) is a web application for centralizing authentication and account creation with moderation. It is written in Python3, Pyramid, Chameleon, LDAP, Tal/Metal, and Bootstrap 5.

# Documentation
All the documentation is in the docs folder.
We use Obsidian notes, so if you see [[A Name]] in our notes, it's a link to the markdown file named "A Name.md".
For an enhanced experience, you can use Obsidian or Markdown Memo in Visual Studio Code.
`docs/fr` contains the French documentation
`docs/en` contains the English documentation

# Development
Clone this repository
```bash
cd YourWorkingFolder
git clone git@github.com:michaellaunay/alirpunkto.git
python3 -m venv alirpunkto
cd alirpunkto
```

Activate this virtual environment
```bash
source bin/activate
```

Update
```bash
bin/pip install --upgrade pip setuptools
pip list --outdated --format=columns | tail -n +3 | awk '{print $1}' | xargs -n1 pip install -U
```

Install pyramid
```bash
pip install pyramid pyramid_chameleon python-dotenv ldap3 pyramid_beaker pyramid_mailer py3dns validate_email cryptography bcrypt python-keycloak pyjwt
```

We need ZODB to store vote and session informations.

# Getting Started

- Change directory into your newly created project if not already there. Your
  current directory should be the same as this README.txt file and setup.py.

```bash
cd alirpunkto
```

- Install the project in editable mode with its testing requirements.

```bash
bin/pip install -e ".[testing]"
```

- Create de var folder

```bash
mkdir -p var/log var/datas var/filestorage var/sessions
```

- Create the secret file containing your keys

```bash
cp .env.example .env
```

Generate a secret whith 

```bash
python3 alirpunkto/generate_secret.py
```

And change the SECRET_KEY inside the .env file.

Here's the translated documentation in English for including in the `README.md` file of your AlirPunkto project, explaining how to add the `alirpunkto/alirpunkto_schema.ldif` schema to OpenLDAP on Ubuntu 22.04:

Add alirpkunto_schema.ldif as describe bellow

- Run your project's tests.

```bash
bin/pytest
```

You should have no error !

- Run your project.
```bash
bin/pserve development.ini
```

---

## Adding AlirPunkto Schema to OpenLDAP on Linux

This section guides you through the steps to integrate the custom `alirpunkto_schema.ldif` schema into an OpenLDAP server on Ubuntu 22.04.

### Prerequisites

- An OpenLDAP server installed on Ubuntu 22.04.
- Administrative rights on the LDAP server.
- The `alirpunkto_schema.ldif` file available in the `alirpunkto` directory of this project.
- You can replace the PEN number with your own before proceeding with the installation.

### Installation Steps

1. **Server Connection**  
   Log into your Ubuntu server where OpenLDAP is installed.

2. **Stopping LDAP Service**  
   Before making any configuration changes, stop the LDAP service to prevent data corruption.
   ```bash
   sudo systemctl stop slapd
   ```

3. **Locating the Schema File**  
   Ensure that the `alirpunkto_schema.ldif` file is present on the server. If not, transfer it to an appropriate directory (e.g., `/tmp`).

4. **Adding the Schema to LDAP Server**  
   Run the following command to add the schema to your LDAP directory:
   ```bash
   sudo apt install schema2ldif
   ldap-schema-manager -i /path/to/alirpunkto_schema.ldif
   ldap-schema-manager -m /path/to/alirpunkto_schema.ldif -n
   ```
   Replace `/path/to/alirpunkto_schema.ldif` with the actual path of the `alirpunkto_schema.ldif` file on your server.

5. **Restarting LDAP Service**  
   After successfully adding the schema, restart the LDAP service:
   ```bash
   sudo systemctl start slapd
   ```

6. **Verification**  
   Verify that the schema has been added correctly. You can do this by checking the OpenLDAP logs or using an LDAP tool to explore the schema configuration.

### Troubleshooting

If you encounter any issues while adding the schema, check the OpenLDAP logs for detailed error information. The logs can often provide useful clues about what might have gone wrong.

### Important Notes

- Ensure you have a backup of the existing LDAP configuration before making changes.
- Any modifications to the LDAP configuration should be carried out with caution, as errors can affect the stability and security of the service.
- Test changes in a development environment before applying them on a production server.

