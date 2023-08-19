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
```

Install pyramid
```bash
pip install pyramid pyramid_chameleon python-dotenv ldap3 pyramid_beaker pyramid_mailer
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
mkdir var
```

- Create the secret file with your keys

```bash
cp .env.example .env
```

And change the secrets inside.

- Run your project's tests.

```bash
bin/pytest
```

You should have no error !

- Run your project.

    bin/pserve development.ini

