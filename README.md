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
cd alirpunkto
```

Create a virtual environment named pyramid, for example
```bash
python3 -m venv pyramid
```

Activate this virtual environment
```bash
source pyramid/bin/activate
```

Update it
```bash
pip install --upgrade pip setuptools
```

Install Pyramid
```bash
pip install pyramid
```

The initial workspace was created with the commands below.
Normally, you won't have to do this again
```bash
pip install cookiecutter
cookiecutter gh:Pylons/pyramid-cookiecutter-starter
```
And select these options
```
project_name: alirpunkto
repo_name: alirpunkto
Select template_language:
2 - chameleon
Choose from 1, 2, 3 [1]: 2
Select backend:
3 - zodb
Choose from 1, 2, 3 [1]: 3
```

We need ZODB to store vote information.


