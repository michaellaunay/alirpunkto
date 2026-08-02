# 14 — Développer avec des agents IA (Claude Code, Codex, Kimi)

Le dépôt embarque un **harnais multi-agents** audité (douzième passage
externe) : `AGENTS.md` est le contrat commun — environnement,
commandes exactes de la CI, conventions de livraison, règles dures et
pièges de tests — lu nativement par Codex et Kimi Code CLI ;
`CLAUDE.md` l'importe (`@AGENTS.md`) et n'ajoute que le spécifique
Claude Code ; `.claude/settings.json` traduit les règles en
permissions vérifiables ; `tests/test_agent_harness.py` verrouille le
tout (validité du JSON, `.env.example` jamais bloqué, parité des
commandes documentées avec les workflows). Ce chapitre explique
comment installer chaque agent et travailler avec, sur ce dépôt
précisément.

Principe commun, quel que soit l'agent : le livrable local est un
**patch numéroté** (`git diff > NNNN-sujet.patch`, ignoré par Git)
qui s'applique avec `git apply` sur un clone vierge de `master` —
jamais de `git push`, le mainteneur fusionne ; chaque changement de
comportement vient avec sa **démonstration rouge/verte** ; le
français est la langue de conversation avec le mainteneur, l'anglais
celle du code et des commits.

## Claude Code

**Prérequis.** Node.js 18 ou plus, et un accès : soit un abonnement
Claude (Pro/Max — Claude Code y est inclus, l'usage est partagé avec
le chat), soit une clé API Anthropic facturée au jeton. Piège connu :
si `ANTHROPIC_API_KEY` traîne dans le shell, Claude Code l'utilise
silencieusement et facture l'API en ignorant l'abonnement — vérifier
avec `echo $ANTHROPIC_API_KEY` avant la première session.

**Installation et premier lancement.**

```bash
npm install -g @anthropic-ai/claude-code
cd ~/chemin/vers/alirpunkto
claude          # première fois : connexion (abonnement ou clé API)
```

Lancé à la racine, Claude Code charge `CLAUDE.md`, qui importe
`AGENTS.md` : l'agent connaît d'emblée la mise en place de
l'environnement (les **deux** verrous hachés dans `.venv`, le
`mkdir -p var`), les commandes exactes de la CI, les trois décisions
du mainteneur à ne jamais rouvrir, et les pièges (la `SECRET_KEY` des
tests doit être une clé Fernet, `get_secret` vide l'environnement,
etc.).

**La politique de permissions en pratique.** `.claude/settings.json`
est versionné et partagé : lecture du dépôt et boucle
pytest/ruff/bandit **silencieuses** ; `git commit`, `git apply`,
`pip install` et `docker` **sur confirmation** ; lecture de `.env`,
`docker/.env*` sensibles et `docker/secrets/`, `git push`, `rm -rf`
et l'édition des trois verrous **refusées**. Le fichier suivi
`.env.example` reste lisible — c'est précisément un fichier à
auditer. Ces règles sont des **garde-fous** sur les appels d'outils,
pas un bac à sable absolu : ne pas les contourner par des commandes
shell équivalentes. Les surcharges personnelles vont dans
`.claude/settings.local.json` (ignoré par Git).

**Exemples de sessions sur AlirPunkto.**

```text
> Prépare l'environnement et lance la suite complète comme la CI.
```

L'agent crée `.venv` depuis `requirements-test.lock` puis
`requirements-quality.lock` (`--require-hashes`), fait `mkdir -p
var`, exporte l'environnement de test (dont une `SECRET_KEY` Fernet)
et exécute pytest avec la couverture — la commande exacte est dans
`AGENTS.md`.

```text
> Le douzième audit demande un sérialiseur LDIF validant (§12).
> Prépare le train 0085 : implémentation, tests rouge/vert,
> patch applicable sur master, message de commit développé
> avec le trailer Refs.
```

```text
> Pourquoi tests/test_ldif_callers.py refuse-t-il mon commentaire ?
```

(Réponse attendue de l'agent : un verrou structurel interdit certains
jetons dans les scripts — on reformule le commentaire, on n'affaiblit
jamais le verrou.)

## Codex (OpenAI)

Codex CLI lit **nativement** `AGENTS.md` à la racine : aucune
configuration supplémentaire n'est nécessaire pour ce dépôt.

**Installation** (Node.js 18+ ; compte ChatGPT Plus/Pro/Team ou clé
API OpenAI) :

```bash
npm install -g @openai/codex     # le paquet est @openai/codex,
cd ~/chemin/vers/alirpunkto      # pas « codex » (paquet sans rapport)
codex
```

Un script d'installation officiel existe aussi
(`https://chatgpt.com/codex/install.sh`) ainsi qu'un cask Homebrew.

**Sur ce dépôt.** Les mêmes exemples de sessions valent tels quels —
le contrat est le même fichier. Particularité **Codex cloud / mode
PR** (documentée dans `AGENTS.md`) : le livrable-patch ignoré par Git
ne convient pas à un espace de travail géré qui prépare une pull
request ; dans ce mode, modifier l'arbre suivi et présenter le diff
résultant — mais ne jamais pousser sans demande explicite du
mainteneur.

## Kimi (Moonshot — Kimi K3 via Kimi Code CLI)

Kimi Code CLI charge lui aussi `AGENTS.md` nativement (sa commande
`/init` sait même en générer un — inutile ici, le fichier existe).
Attention à la nuance : cette compatibilité appartient au **client**
Kimi Code CLI, pas au modèle Kimi K3 — via l'API, une interface web
ou un autre orchestrateur, fournir explicitement `AGENTS.md` comme
instructions de projet.

**Installation** (abonnement Kimi ou clé API ; `/login` au premier
lancement) :

```bash
curl -fsSL https://code.kimi.com/kimi-code/install.sh | bash
# ou, avec Node.js ≥ 22.19 : npm install -g @moonshot-ai/kimi-code
cd ~/chemin/vers/alirpunkto
kimi
```

Piège documenté : le paquet PyPI `kimi-code` correspond à l'ancien
agent Python — le Kimi Code actuel vit sur npm ; `kimi --version` en
`0.x` confirme le bon produit. L'état personnel du CLI
(`.kimi-code/local.toml`) est ignoré par Git.

## Vérifier le harnais lui-même

Le harnais est testé comme le reste du code :

```bash
.venv/bin/python -m pytest tests/test_agent_harness.py -q
```

Ces verrous garantissent notamment que les commandes citées dans
`AGENTS.md` restent la copie exacte de celles des workflows — une
dérive de la CI ou de la documentation fait échouer la suite. Détail
des constats d'origine : versement du douzième passage,
`docs/fr/audits/20260802_audit_externe_chatgpt_alirpunkto_12e_passage.md`.
