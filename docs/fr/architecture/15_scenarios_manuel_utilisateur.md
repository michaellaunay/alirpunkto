# 15. Scénarios de validation et manuel utilisateur auto-généré

## Principe

Le manuel utilisateur ne s'écrit pas : il se **génère**. Chaque
parcours important de l'application est rejoué par un vrai
navigateur (Playwright) contre la pile Docker de test, écran par
écran ; chaque étape capture l'écran et enregistre une légende **en
français et en anglais**. Le générateur assemble captures et
légendes en pages de manuel bilingues, publiées en artefact CI à
chaque exécution. Conséquence structurelle : la documentation
utilisateur ne peut plus mentir — chaque image provient d'un
parcours que l'intégration continue vient de valider, et un écran
qui change casse le scénario avant de périmer le manuel.

## Architecture

- `tools/e2e_scenarios/framework.py` — la classe `Scenario` :
  `step(page, slug, fr, en)` capture l'écran (`<scenario>_NN_<slug>.png`)
  et enregistre les deux légendes dans `manifest.json` ; la
  signature **impose** le bilinguisme. `fetch_email(recipient)`
  lit la boîte de capture du Postfix de test (transport remplaçable
  par `E2E_MAIL_CMD`). `solve_all_challenges(body)` résout les
  quatre défis mathématiques du courriel d'inscription **sans
  dépendre des opérateurs** : la structure `n1 × n2 + n3` étant
  fixe, il extrait les trois premiers mots-nombres de la ligne
  (dictionnaires anglais, français, espéranto) — nécessité apprise
  sur pièces : le gabarit du courriel sort en espéranto et le
  catalogue anglais rend « times » par « multiplied by ».
- `tools/e2e_scenarios/scenario_registration.py` — les deux
  premiers parcours : inscription d'un membre ordinaire (jusqu'à la
  première connexion du compte créé) et candidature de Coopérateur
  (jusqu'à l'attente des vérificateurs). Chaque soumission
  **vérifie l'écran atteint** avant de le légender : un refus
  produit une capture d'échec explicite, jamais une légende de
  succès sur un écran d'erreur.
- `tools/e2e_scenarios/run_all.py` — l'exécuteur strict.
- `tools/generate_user_manual.py` — manifeste + captures →
  `manual/fr/*.md` et `manual/en/*.md` avec images et index.

## La chaîne postale de test

Le Postfix de la pile de test est un **puits hors-ligne**
(`start_test_postfix.sh`) : il accepte tout et ne relaie rien.
Avec `POSTFIX_LOCAL_CAPTURE=1` (posé par le compose de test), les
courriels **du domaine de test** sont conservés dans la boîte
locale de l'utilisateur `catchall` — livrés en Maildir
(`/home/catchall/Maildir/`, un fichier par message, car
`home_mailbox = Maildir/`) — tandis que tout le reste demeure
détruit : rien ne sort jamais de la pile. `maillog_file =
/dev/stdout` rend les livraisons visibles dans `docker logs`.

## Exploitation

En CI : le workflow `test-stack` exécute les scénarios après le
parcours de connexion, puis publie deux artefacts — `user-manual`
(les pages fr/en illustrées) et `e2e-screenshots` (toutes les
captures, échecs compris : le diagnostic est intégré).

En local :

    bash docker/init_test.sh
    docker compose --env-file docker/.env.test \
        -f docker/test-docker-compose.yaml up -d --build
    python -m venv /tmp/e2e-venv && /tmp/e2e-venv/bin/pip install \
        --require-hashes -r requirements-e2e.lock
    /tmp/e2e-venv/bin/playwright install chromium
    cd tools/e2e_scenarios && E2E_SHOT_DIR=/tmp/e2e-shots \
        /tmp/e2e-venv/bin/python run_all.py
    /tmp/e2e-venv/bin/python ../generate_user_manual.py \
        /tmp/e2e-shots /tmp/user-manual

## Écrire un nouveau scénario

Créer `scenario_<nom>.py`, instancier `Scenario(slug, titre_fr,
titre_en)`, dérouler le parcours en appelant `step()` à chaque
écran — toujours les deux légendes — puis `close()`. Enregistrer le
parcours dans `run_all.py`. Règles apprises sur pièces : piloter
les **widgets réels** (le choix d'adhésion est un `<select>` ; les
formulaires deform soumettent par `<button type="submit">`, d'où le
sélecteur composite de `_submit()` ; le champ date deform s'appelle
`date`) ; **vérifier chaque écran atteint** avant de le légender ;
ne jamais supposer la langue du courriel.

## Ce que les scénarios ont déjà attrapé

Leur cinquième exécution a trouvé un défaut que les tests unitaires
ne pouvaient pas voir : `preferredLanguage` était posé sans garde à
la création LDAP, or le parcours ordinaire ne saisit pas de langue
— **aucun membre ordinaire ne pouvait être créé par le formulaire
d'inscription** (train 0095 : garde sur `lang1` et ceinture qui
élimine tout attribut vide avant `conn.add`). C'est la raison
d'être de ces parcours : vivre ce que vivent les utilisateurs.

Prochain scénario de la série : le **vote des vérificateurs**, qui
fera du candidat Coopérateur un Coopérateur de plein droit.
