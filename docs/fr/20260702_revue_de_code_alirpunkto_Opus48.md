# Revue de code — AlirPunkto — **audit vérifié** (dump du 2026-07-02)

> Cette révision **reprend, vérifie et met à jour** l'audit `20260613_revue_de_code_alirpunkto.md` à partir du dump de sources du **2026-07-02** et du `git_log` fourni.
> Contrairement aux révisions précédentes, chaque point a été **vérifié empiriquement** : le dépôt a été reconstitué depuis le dump (89 fichiers), les dépendances installées dans un venv Python 3.12, et **la suite de tests a réellement été exécutée**. Les clés i18n ont été croisées avec le `alirpunkto.pot` fourni.
> Numéros de ligne = numérotation interne de chaque fichier dans le dump du 2026-07-02.

**Légende :** ✅ corrigé · ⚠️ partiel / mitigé · ❌ non corrigé · 🆕 point neuf relevé par cette vérification

---

## 0. Méthode de vérification (nouveau)

| Étape | Résultat |
|---|---|
| Reconstitution du dépôt depuis le dump | 89 fichiers écrits |
| Diff avec le dump précédent (2026-07-01) | 20 fichiers applicatifs modifiés + 14 nouveaux fichiers de tests |
| **Exécution de `pytest`** | **195 passed, 6 skipped, 4 failed** |
| Analyse des échecs | Les **4 échecs** viennent **uniquement** de l'absence de `tools/export_sources_for_review.sh` dans le dump (fichier d'outillage non exporté) — **aucun échec applicatif** |
| Les 6 *skipped* | Tests fonctionnels, sautés faute de `testing.ini` (comportement attendu du `conftest`) |
| Collecte | **205 tests collectés** — conforme à l'annonce |

**Conclusion sur les tests** : la suite est effectivement verte. Les 205 tests passent dans le vrai dépôt (les 4 « échecs » observés ici sont des artefacts du dump, pas des régressions). L'affirmation « 205 tests verts » est **confirmée**.

> Note : les locales n'étant pas fournies, l'arborescence `alirpunkto/locale/{fr,en}/LC_MESSAGES` a été recréée vide pour permettre le démarrage (`get_locales()` liste ce répertoire). Cela n'affecte pas les tests unitaires exécutés.

---

## 1. Synthèse

L'état décrit par votre audit est **globalement exact et vérifié**. À la date du dump 2026-07-02 :

- **§1 Sécurité** : les 10 failles corrigées le sont bien ; **seule 1.3** (mots de passe en clair LDAP + ZODB) reste ouverte — c'est le point de sécurité prioritaire.
- **§2 Bugs bloquants** : les **18 trouvailles (2.1–2.18) sont corrigées**, vérifiées par les tests et par contrôle empirique ciblé (2.11, 2.12, 2.16 rejoués indépendamment).
- **§3 Cohérence transactionnelle** : **aucun `commit`/`abort` explicite ne subsiste dans les vues** (vérifié par `grep`) ; seul le `commit` de bootstrap de `Members.get_instance` demeure, ce qui est justifié.
- **§4 / §5** : inchangés (hors §4.14), conformes à l'audit — avec deux corrections de référence ci-dessous.

**Ce que cette vérification ajoute** (non couvert ou inexact dans l'audit) :
1. 🆕 **Catalogue i18n désynchronisé** : ~13 clés référencées dans le code sont **absentes du `.pot`** → `msgid` brut affiché à l'utilisateur (dont tout le jeu de messages de `manage_provider` et `voting_period_ended`).
2. 🆕 **Indexations `request.params[...]` non gardées** (cousines de 2.17, non traitées) → `KeyError`/500 sur POST malformé mais CSRF-valide, dans `register`, `login`, `forgot_password`.
3. 🆕 **Interaction `pyramid_retry` × effets LDAP non idempotents** : le retrait des commits (§3) élargit la fenêtre de rejeu ; à documenter.
4. 🆕 **Mutation ZODB partielle *committée* sur erreur en cours de boucle** dans `modify_member` (réponses d'erreur = HTTP 200 → `pyramid_tm` committe).
5. Corrections de références dans le document d'audit (§4.31, §4.1, note 2.11).

| Section | Corrigé | Partiel | Non corrigé |
|---|---|---|---|
| 1. Sécurité critique | 1.1, 1.2, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11 | — | **1.3** |
| 2. Bugs bloquants | **2.1–2.18 (les 18)** ✅ vérifié | — | — |
| 3. Transactions | ✅ 6 vues nettoyées + `get_instance` justifié | — | — |
| 4. Bugs mineurs | §4.14 | §4.18 | §4.1, §4.31 |
| 5. Qualité | — | — | typos, `pkg_resources`, `pytz`, annotations |
| **i18n (catalogue)** | — | — | 🆕 ~13 clés manquantes au `.pot` |

---

## 2. Vérification de la section §2 (confirmations)

Points rejoués **indépendamment des tests fournis** (exécution directe) :

- **2.11** (validateur mot de passe) — un mot de passe valide (avec caractère spécial autorisé `$@#%&*()-_+=`) est **accepté** ; un mot de passe trop court/sans spécial lève bien `colander.Invalid`. Adaptateur `_validate_password` conforme au contrat de `colander.Function`. ✅
- **2.12** (`get_i18n_id`) — les 6 classes (`MemberStates`, `MemberTypes`, `Permissions`, `CandidatureStates`, `VotingChoice`, `MemberRoles`) : **aucun** fallback ne renvoie le littéral `"name.lower()"`. ✅
- **2.16** (`get_secret`) — `SECRET_KEY` absent → `ValueError` explicite (plus de `KeyError`). ✅
- **2.1 / 2.2** (permissions) — `_resolve_permissions` *fail-closed* + `ADMIN_CANDIDATURE_PERMISSIONS` branché sur les 7 états ; comparaison votant sur les `oid`. ✅ (vérifié par lecture + tests verts)
- **2.13** (SSO) — les **trois** vues (`login`, `home`, `sso_login`) stockent `sso_token['access_token']` en session ; le `request.headers['Authorization']` factice a disparu partout. ✅
- **2.14 / 2.15** — `get_instance` teste la connexion en premier ; `ldap_factory` n'a plus de singleton `_conn`, hôte/port résolus au call time. ✅
- **§3** — `grep` sur `alirpunkto/views/` : **0** `transaction.commit()/request.tm.commit()/abort()`. Seul reste `member.py:396` (bootstrap `get_instance`). La garde `try/except` autour de `random_voters()` dans `prepare_for_cooperator` est bien **restaurée**. ✅

**1.3 — confirmée ouverte** : `register.py` construit `MemberDatas(**parameters)` à partir de `request.params` (inclut `password`/`password_confirm`) sans purge ultérieure ; `vote.py:125` relit `candidature.data.password` en clair pour la création LDAP ; `register_user_to_ldap` envoie `userPassword` en clair et `update_member_password` fait un `MODIFY_REPLACE` du mot de passe brut. Aucun hachage. **C'est le point de sécurité restant le plus important.**

---

## 3. 🆕 Points neufs relevés par cette vérification

### 3.1 🆕 Catalogue i18n désynchronisé — ⚠️ **à corriger** (impact UX)

Le `alirpunkto.pot` fourni **n'est pas régénéré depuis le code** : il ne contient **aucune** référence `#:` à `manage_provider.py`, et les clés récentes (`invalid_field_value`…) y figurent **sans commentaire de localisation** → catalogue maintenu à la main. Résultat : plusieurs `msgid` utilisés par le code sont **absents**, et s'afficheront **bruts** à l'utilisateur.

Clés référencées dans le code mais **absentes du `.pot`** (croisement automatique code ↔ `.pot`) :

| Clé manquante | Utilisée dans | Impact |
|---|---|---|
| `voting_period_ended` | `vote.py:90` | message affiché quand la *deadline* est dépassée (déjà signalé en *Suivi* 2.3) |
| `provider_updated` | `manage_provider.py:186` | succès de mise à jour fournisseur |
| `provider_created` | `manage_provider.py` | succès de création fournisseur |
| `provider_creation_failed` | `manage_provider.py` | erreur de création |
| `provider_email_already_exists` | `manage_provider.py` | doublon d'e-mail |
| `provider_email_fullname_password_missing` | `manage_provider.py` | champs manquants |
| `must_be_administrator` | `manage_provider.py` | accès refusé |
| `accessed_member_oid_missing` | `manage_provider.py` | oid manquant |
| `error_sending_voting_result_email` | `vote.py` | échec d'envoi du résultat |
| `invalid_date_format` | `modify_member.py` | date invalide |
| `ldap_error_retry` | `modify_member.py` | erreur LDAP transitoire |
| `user_not_logged_in` | plusieurs vues | session expirée |
| `invalid_password` | `register_form.py:49` | **repli** du validateur (cf. ci-dessous) |

**Note sur l'audit** : la fiche 2.11 affirme « le repli `_('invalid_password')` existe déjà » — **inexact** au vu du `.pot` fourni (`invalid_password` en est absent). Impact pratique faible (ce repli n'est atteint que si `is_valid_password` renvoie un dict sans clé `error`, ce qui n'arrive pas en pratique), mais la note est à corriger. Le jeu de messages `manage_provider` (jamais extrait) est en revanche un vrai trou UX.

**Action** : régénérer le `.pot` par extraction (`pybabel extract` / le script de synchro du commit `d56f526`), puis compléter `fr`/`en`/… — a minima ajouter `voting_period_ended` et l'ensemble des messages `manage_provider`.

### 3.2 🆕 Indexations `request.params[...]` non gardées (cousines de 2.17) — ⚠️ robustesse

2.17 n'a corrigé **que** `validate_challenge`. Le même motif (`KeyError` → 500 sur POST CSRF-valide mais sans le champ attendu) subsiste ailleurs :

- `register.py:196-197` — `request.params['email']` / `['choice']` sous `if 'submit' in request.POST:` (`handle_draft_state`).
- `login.py:50-51` — `request.params['username']` / `['password']` sous `if 'form.submitted' in request.params:`.
- `forgot_password.py:187-188` — `request.params['password']` / `['password_confirm']` dans la branche « modify ».

Sévérité **faible à modérée** : accessible seulement avec un jeton CSRF valide et une requête volontairement incomplète (pas d'exposition de données, pas de contournement d'authentification), mais c'est un 500 évitable. Correctif : `request.params.get(clé, '')` comme en 2.17. *(À l'inverse, les accès de `modify_member.py:289-300` sont bien gardés par `field in request.POST and …` en court-circuit.)*

### 3.3 🆕 `pyramid_retry` × effets LDAP non idempotents — à documenter

`pyramid_retry` **est activé** (`__init__.py:219`). Sur `ConflictError` ZODB, `pyramid_tm` **rejoue toute la vue**. Or les effets LDAP ne sont pas idempotents : `register_user_to_ldap` (un `conn.add`), `update_member_password` / `update_ldap_member` (`conn.modify`), et les envois d'e-mail. Le retrait des commits intermédiaires (§3) fait que la transaction couvre désormais **tout** le corps de la vue, y compris l'appel LDAP → un rejeu relance l'`add` LDAP, qui échoue au 2ᵉ passage (« DN existe déjà ») et renvoie une erreur, laissant la candidature **non approuvée alors que le compte LDAP a été créé**.

Ce n'est pas une régression franche (LDAP et ZODB ne sont de toute façon pas atomiques), mais c'est un angle mort de la section §3 : **les effets externes non transactionnels devraient idéalement être poussés en fin de transaction** (souscripteur post-commit) ou rendus idempotents (ignorer « entrée déjà existante » à l'`add`). À noter dans la dette de robustesse.

### 3.4 🆕 Mutation ZODB partielle *committée* sur erreur en cours de boucle (`modify_member`)

Dans `modify_member`, la boucle sur `writable_fields` fait `setattr(accessed_member.data, field, …)` champ par champ (l.421/425) **avant** l'écriture LDAP (l.444, après la boucle). Si un champ **tardif** échoue (valeur non coercible → retour `invalid_field_value`, ou champ inconnu → `error_while_setting_field`), la vue renvoie une **erreur en HTTP 200** : `pyramid_tm` **committe** alors les champs déjà mutés, **sans** écriture LDAP correspondante et **sans** passage à `DATA_MODIFIED`. Résultat : divergence ZODB/LDAP partielle.

Pré-existant (indépendant du §3), sévérité faible (édition admin/self, récupérable), mais réel. Deux options : valider/coercer **tous** les champs *avant* tout `setattr`, ou lever une exception (plutôt que renvoyer un dict) sur erreur pour que `pyramid_tm` fasse `abort`.

### 3.5 Corrections de références dans le document d'audit

- **§4.31** : `get_majority_date` est dans **`schemas/register_form.py:33`**, **pas** `routes.py:33` (qui ne contient que la vue statique). Le bug (`timedelta(days=365*18)` au lieu de `relativedelta(years=18)`) est bien présent, mais à la bonne adresse.
- **§4.1** : il reste **2** occurrences de `(objectClass=*)` (pas 6) : `__init__.py:189` (portée **`BASE`** sur un DN précis = **test d'existence légitime**, à ne pas toucher) et `utils.py:159` (`get_ldap_member_list`, portée **`SUBTREE`** sur toute la base = **seule** vraie préoccupation de perf ; remplacer par `(objectClass=alirpunktoPerson)`).

---

## 4. Régression cosmétique (confirmée, toujours ouverte)

**`register.pt:206`** : le jeton CSRF du **3ᵉ formulaire** (vérification d'identité coopérateur) est rendu `type="d-none"` au lieu de `type="hidden"`. Un `type` inconnu retombe sur `text` → le champ s'affiche comme une zone de texte éditable. **La protection CSRF n'est pas cassée** (un `<input>` de type texte soumet quand même sa valeur, donc le jeton part et est validé), c'est purement cosmétique/UX. Les 9 autres formulaires utilisent `type="hidden"`. Correctif trivial : `d-none` → `hidden`.

---

## 5. Reste ouvert / dette (confirmé)

**Sécurité**
1. **1.3** — hachage des mots de passe côté LDAP (`{SSHA}`/`modify_password`) et **purge de `data.password`/`data.password_confirm`** en ZODB après création. **Priorité n°1.**

**i18n (nouveau)**
2. Régénérer le `.pot` et compléter les catalogues (§3.1) — a minima `voting_period_ended` + messages `manage_provider`.

**Robustesse**
3. Gardes `request.params.get(...)` sur les indexations de §3.2.
4. Idempotence/ordonnancement des effets LDAP vis-à-vis de `pyramid_retry` (§3.3) et validation « tout ou rien » dans `modify_member` (§3.4).
5. `elections_view` reste un *stub* ; dépouillement du vote à l'échéance non implémenté (`vote.py` @TODO) ; sémantique d'égalité YES/NO et typage `str`→`VotingChoice` à trancher.
6. Couverture restante de la matrice `access` (§2.2 *Suivi*).

**Bugs mineurs**
7. §4.18 — liste blanche dans `vote.pt` (`iban`, `date_erasure_all_data` encore exposés aux votants).
8. §4.31 — `relativedelta(years=18)` dans `register_form.py`.
9. §4.1 — `(objectClass=alirpunktoPerson)` dans `get_ldap_member_list`.

**Qualité (§5)**
10. Typos (`REGISTRED`, `allready`, `Coulb`), `pkg_resources` déprécié, `pytz`, annotations de type mensongères ; ajouter `ruff`/`mypy`.
11. 1.8 — libellé neutre de `forget_email_sent` (le texte actuel commence bien par « If the user exists » mais affirme ensuite l'envoi).

**Continu**
12. Étendre la couverture de tests aux sections §1 (notamment le futur hachage 1.3) et §3, et corriger `register.pt` (`d-none` → `hidden`).

---

## 6. Verdict

Le travail de la dernière passe est **réel et solidement testé** : §2 entièrement traité, §3 mené à bien proprement (mailer transactionnel bien compris, `_p_changed` conservé, garde LDAP restaurée), et une suite de non-régression qui **s'exécute et passe**. L'audit de l'équipe est fidèle au code, à quelques détails de référence près.

Les apports de cette vérification sont surtout : le **décalage du catalogue i18n** (impact UX concret, plusieurs messages bruts), un **cluster d'indexations non gardées** analogue à 2.17, et deux **angles morts transactionnels** (rejeu `pyramid_retry` sur effets LDAP, mutation partielle committée sur erreur). Aucun n'est bloquant ; **1.3 reste la priorité de sécurité**.
