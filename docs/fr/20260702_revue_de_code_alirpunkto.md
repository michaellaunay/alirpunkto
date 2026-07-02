# Revue de code — AlirPunkto — audit **refait** (dump du 2026-07-02)

> **Périmètre** : dump `20260702_alirpunkto_sources.txt` (75 fichiers applicatifs + tests + docker), tête de dépôt `b1cfdf9` (2026-07-01 18:18), catalogue `alirpunkto.pot` fourni séparément (locales exclues du dump).
> **Méthode** : chaque affirmation ci-dessous a été **vérifiée empiriquement** — code extrait dans une arborescence réelle, suite de tests exécutée (pytest, venv Python 3.12 avec les dépendances du projet), greps de contrôle sur les points sensibles, croisement code ↔ catalogue i18n.
> Les numéros de ligne correspondent à la numérotation interne de chaque fichier dans le dump du 2026-07-02.
>
> Cet audit **remplace** les révisions précédentes (2026-06-13 → 2026-07-01) : chaque trouvaille historique est reprise avec son état constaté, puis viennent les observations nouvelles de cette passe.

**Légende :** ✅ corrigé (vérifié) · ⚠️ partiel / réserve · ❌ non corrigé · 🆕 nouveau / régression

---

## Synthèse

Le tableau de bord a radicalement changé depuis l'audit d'origine (2026-06-12). **Les sections 2 (bugs bloquants) et 3 (cohérence transactionnelle) sont soldées et couvertes par des tests de non-régression.** La suite de tests exécutée sur ce dump donne **195 verts + 6 skippés + 4 échecs d'artefact** (voir § Tests) — soit **205/205 verts dans le dépôt réel**, ce qui concorde avec ce qu'annonce l'équipe.

**Il ne reste qu'une seule faille de sécurité : la 1.3** (mots de passe stockés en clair, côté LDAP *et* côté ZODB). C'est désormais, de loin, le chantier prioritaire.

Cette passe ajoute par ailleurs quatre lots d'observations nouvelles : **(N1)** la régression cosmétique `register.pt` (`type="d-none"`) toujours présente ; **(N2)** un petit cluster d'indexations `request.params[...]` non gardées (KeyError → 500 sur POST malformé) ; **(N3)** **13 clés i18n utilisées par le code mais absentes du `.pot`** — dont `voting_period_ended`, pourtant identifiée dès le correctif 2.3 ; **(N4)** trois nuances transactionnelles résiduelles (commits partiels sur retour d'erreur, rejeu `pyramid_retry` × effets LDAP non idempotents, absence d'atomicité ZODB/LDAP) qui méritent d'être actées comme limites documentées.

Enfin, deux **corrections d'erreurs de l'audit précédent** lui-même : §4.31 pointait le mauvais fichier, et §4.1 surestimait le nombre d'occurrences réellement problématiques.

| Section | Corrigé (vérifié) | Réserve / partiel | Non corrigé |
|---|---|---|---|
| 1. Sécurité critique | 1.1, 1.2, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 1.11 | — | **1.3** |
| 2. Bugs bloquants | **2.1 → 2.18 (les 18)** | nits résiduels (imports morts 2.4, stub 2.5) | — |
| 3. Transactions | 6 vues nettoyées, 1 seul `commit` restant (bootstrap justifié) | 🆕 3 nuances documentées (N4) | — |
| 4. Bugs mineurs | 4.14 | 4.1 (1 occurrence réelle sur 2), 4.18 | 4.31, autres §4 non retouchés |
| 5. Qualité | — | — | typos, `pkg_resources`, `pytz`, annotations |
| 🆕 Nouveaux | — | N1 (`register.pt`), N2 (KeyError), **N3 (i18n)**, N4 (transactions) | — |

---

## Résultats de la suite de tests (exécution du 2026-07-02)

```
205 collectés — 195 passed, 6 skipped, 4 failed (2.72 s)
```

- **25 fichiers de tests, 142 fonctions `test_`** (le paramétrage porte le total à 205 cas).
- Les **6 skippés** sont les tests fonctionnels (`tests/test_functional.py`), qui exigent un `testing.ini` volontairement absent du dump — comportement prévu par `conftest.py`.
- Les **4 échecs** sont tous des artefacts du dump, pas du code : `test_export_sources_for_review.py` (3 tests) et `test_local_docker_stack.py::test_shell_scripts_are_syntax_valid[tools/export_sources_for_review.sh]` cherchent `tools/export_sources_for_review.sh`, qui vit dans `tools/` — un répertoire que le script d'export lui-même n'inclut pas (il n'exporte que `alirpunkto tests docker`). Dans le dépôt réel, ces 4 tests passent : **le « 205 verts » annoncé est confirmé**.
- Aucune erreur applicative, aucune erreur de collection, aucun test flaky observé sur deux exécutions.

*Nit tests* : `tests/test_functional.py:5` pose `pytest.mark.functional` sans l'enregistrer → `PytestUnknownMarkWarning`. Ajouter `markers = functional` dans la config pytest.

---

## 1. Failles de sécurité critiques

### 1.1 Cookie de session signé avec une constante publique — ✅ corrigé
La fabrique de session dérive le secret de la **valeur** de `SECRET_KEY` (via `get_secret`), et pose `httponly=True, secure=True, samesite='Lax'`. Inchangé depuis la vérification précédente ; rien à redire.

### 1.2 Mots de passe en clair dans les logs — ✅ corrigé
`encrypt_secret_for_logs()` (`secret_manager.py:59-92`, RSA-OAEP/SHA-256 sur clé publique d'environnement, marqueurs explicites `<disabled>`/`<no-public-key>`/`<encryption-error>`) est appliqué partout où un mot de passe était journalisé (`login.py`, `forgot_password.py`, `utils.py::register_user_to_ldap` — qui retire en plus `userPassword` du dict loggé via `safe_attributes`).

### 1.3 Mots de passe stockés en clair — ❌ **non corrigé — SEULE FAILLE RESTANTE**
Toujours vrai sur les deux plans, vérifié dans ce dump :

- **LDAP** — `utils.py:968` : `register_user_to_ldap` envoie `'userPassword': password` **en clair** à la création ; `utils.py:1094` : `update_member_password` fait `MODIFY_REPLACE` avec le mot de passe **brut**. Aucun appel à `ldap3...hashed()` ni à `conn.extend.standard.modify_password()` dans le code. Seuls les comptes bootstrap du LDIF sont pré-hachés `{SSHA}`. Si OpenLDAP n'est pas configuré avec une politique de hachage à l'écriture (`ppolicy`/`pw-sha2` + `olcPasswordHash`), tout mot de passe applicatif est stocké en clair dans l'annuaire.
- **ZODB** — `register.py:508` recopie tous les champs de `request.params` présents dans `MemberDatas.__dataclass_fields__` — **dont `password` et `password_confirm`** — puis `register.py:550` construit `MemberDatas(**parameters)` : le mot de passe du candidat est **persisté en clair dans la ZODB** et n'est **jamais purgé**. Il y reste après approbation : `vote.py:125` le relit (`candidature.data.password`) pour créer le compte LDAP au moment du vote final.

**Plan de correction suggéré (dans l'ordre) :**
1. *LDAP* : hacher côté application avant tout `add`/`modify` — `from ldap3.utils.hashed import hashed` puis `hashed(HASHED_SALTED_SHA, password)` (ou `HASHED_SALTED_SHA512`) dans `register_user_to_ldap` et `update_member_password`. Alternative : `conn.extend.standard.modify_password(dn, new_password=...)` qui laisse le serveur hacher selon `olcPasswordHash`. Vérifier ensuite que `check_password` (bind LDAP) fonctionne toujours — le bind compare côté serveur, donc oui.
2. *ZODB* : le flux a réellement besoin du mot de passe entre l'inscription et l'approbation (création LDAP différée au vote). Deux options : **(a)** chiffrer `data.password` au repos (Fernet avec le secret applicatif existant — moindre effort, protège les sauvegardes/dumps ZODB) ; **(b)** mieux : créer l'entrée LDAP dès `ProcessRegistration` dans un état désactivé (`isActive=False`), n'activer qu'à l'approbation, et **ne jamais stocker** le mot de passe en ZODB.
3. Dans tous les cas : après la création LDAP réussie (`vote.py`), **purger** `candidature.data.password = None` et `password_confirm = None` (+ `_p_changed`), et écrire un petit script de migration qui purge/écrase les mots de passe des candidatures existantes dans la base de production.
4. Ajouter un test de non-régression : après approbation, `candidature.data.password is None` ; et l'attribut LDAP `userPassword` commence par `{SSHA` (si option 1).

### 1.4 Injection de filtre LDAP — ✅ corrigé
`escape_filter_chars` enveloppe chaque valeur utilisateur dans les cinq filtres concernés (`get_member_by_email`, `is_valid_unique_pseudonym`, `update_member_from_ldap`, `get_oid_from_pseudonym`, `login.check_password`). Vérifié présent dans ce dump.

### 1.5 CSRF non vérifié — ✅ corrigé
`__init__.py:215` : `config.set_default_csrf_options(require_csrf=True)` ; les 10 formulaires manuels portent le jeton. **Deux réserves de suivi** : la régression cosmétique `register.pt:206` (voir 🆕 N1), et `register.py:444` où `#form.validate(items)` reste commenté (la validation de schéma colander est toujours absente du parcours d'inscription — sans impact CSRF, mais la validation serveur des champs repose alors uniquement sur les contrôles manuels de la vue).

### 1.6 Comparaison de mot de passe admin non constante — ✅ corrigé
`utils.py::is_admin` (l.1210-1218) : double `hmac.compare_digest` sur octets UTF-8, les deux comparaisons évaluées avant combinaison. Conforme.

### 1.7 `get_email` : traversal de template — ✅ corrigé
`email_id` validé par `re.fullmatch('[a-z0-9_]+')` avant construction du chemin ; liste noire illusoire supprimée.

### 1.8 Énumération d'utilisateurs — ✅ corrigé, **suivi libellé soldé**
Les cinq sorties de l'étape `submit` de `forgot_password.py` renvoient un dict strictement identique. **Nouveau constat de cette passe** : le libellé `forget_email_sent` du `.pot` (l.706-707) est désormais **neutre et conditionnel** — « *If the user exists, an e-mail has been sent…* » — ce qui solde l'exigence de suivi (reste à vérifier que les `.po` traduits, non fournis, ont suivi ; le commit `d56f526` « synchronize translations » le laisse penser). La clé orpheline `forget_admin_user` est en revanche **toujours dans le catalogue** (`.pot:702`) — nit facultatif. La limite résiduelle par canal temporel (envoi synchro plus lent quand le compte existe) demeure hors périmètre.

### 1.9 Liens de réinitialisation sans expiration — ✅ corrigé
`decrypt_oid` passe un TTL à `fernet.decrypt` (`OID_LINK_TTL_SECONDS`, 24 h par défaut, surchargeable par env et par appel, lu à l'exécution).

### 1.10 `decrypt_oid` lève au lieu de retourner `None` — ✅ corrigé
Retour `(None, None)` sur jeton invalide/malformé/expiré ; `get_candidature_from_request` durci (tous les modes d'échec → `None`).

### 1.11 Branding pris dans la requête — ✅ corrigé
`login_view`, `sso_login.callback_view` et `elections_view` lisent les constantes `SITE_NAME`/`DOMAIN_NAME`/`ORGANIZATION_DETAILS`. Plus aucune lecture de ces clés depuis `request.params`.

---

## 2. Bugs bloquants — ✅ **2.1 → 2.18 : les dix-huit sont corrigés et testés**

Chaque point ci-dessous a été re-vérifié dans le code du 2026-07-02 (et la suite de tests qui les couvre a été exécutée — voir § Tests).

### 2.1 Vérificateurs sans permissions — ✅
`model_permissions.py:758` : la branche `voter` compare `accessor.oid in {voter.oid for voter in accessed.voters}`. Testé (`test_model_permissions_access.py`).

### 2.2 `KeyError` sur les couples (rôle, état) — ✅
`_resolve_permissions` (`model_permissions.py:699-713`) : *fail-closed* (`NO_MEMBER_PERMISSIONS`) + `warning` identifiant la cellule manquante. `ADMIN_CANDIDATURE_PERMISSIONS` (l.156-163, lecture seule, champs membre hérités de la politique admin donc IBAN masqué) branché sur les 7 états de candidature de `access['Administrator']` (l.560-566). Testé.

### 2.3 Vote jamais persisté — ✅
`vote.py:111` : `candidature._p_changed = True` après `voter.vote = vote` ; garde de *deadline* (l.80-94, deadline naïve normalisée UTC) ; approbation conditionnée au retour `{'status':'success'}` de `register_user_to_ldap`. Le test clé (`test_vote.py`) rouvre un vrai `FileStorage` pour prouver la persistance. *(Réserve i18n : la clé `voting_period_ended` renvoyée l.90 est absente du catalogue — voir 🆕 N3.)*

### 2.4 `manage_provider.py` branches création/mise à jour — ✅ (nits résiduels)
La branche `update` (l.142-186) est **réécrite proprement** : `is_valid_email(new_email, request)` avec le bon arity, `update_member_password` réellement appelé et son statut vérifié, `update_ldap_member(..., fields_to_update=['email'])` avec une **liste**, passage à `MemberStates.DATA_MODIFIED`, plus aucun commit explicite. Le doublon à la création est détecté par `any(existing.email == provider_email for existing in providers)` (l.110) au lieu du `in` cassé. **Nits** : imports morts résiduels — `RegisterForm` (l.33), `Translator` (l.34), `deform` (l.35) et le dict mort `manage_provider_schema` (l.45) ne sont plus utilisés → à supprimer.

### 2.5 `elections.py` plantage — ✅ (mais toujours un *stub*)
Plus de `TypeError` ; la vue renvoie toujours `{"elections": []}`, `candidatures` est assigné/inutilisé (F841) et `logged_in`/`username` sont encore lus depuis `request.params` (sans impact sécurité : valeurs non utilisées pour une décision). Le filtrage des élections reste à écrire (TODO posés).

### 2.6 `update_ldap_member` mapping incohérent — ✅
Le défaut de `fields_to_update` liste les **noms modèle** que le corps teste ; `lang2`/`lang3` en `MODIFY_REPLACE` (valeur ou liste vide), plus de `MODIFY_DELETE` sur attribut absent ; `cooperativeBehaviourMark`/`numberSharesOwned` sérialisés en `str`. Testé (`test_ldap_utils.py`).

### 2.7 `modify_member.py` retour mal interprété + mot de passe inopérant — ✅
`sending_success.get('status') != 'success'` (l.443) au lieu du test de vérité ; la branche mot de passe appelle réellement `update_member_password` (l.383) et vérifie son résultat ; coercition des valeurs de formulaire vers les types déclarés du modèle via `get_type_hints(MemberDatas)` (l.51) et `_coerce_member_data_value` (l.54-70) — corrige aussi les updates LDAP parasites dus aux comparaisons `str` vs typé ; template `check_new_email` (plus `reset_password_email`). Testé (`test_modify_member.py`, `test_check_new_email.py`).

### 2.8 `logout` : `KeyError` sur `?username=` — ✅
`utils.py:1601` : `request.session.pop('username', None)` — le nettoyage piloté par paramètre d'URL non gardé a disparu.

### 2.9 Contrat de retour `register_user_to_ldap` — ✅
Chemin « pseudonyme invalide » normalisé en `{'status':'error','message':…, **error}` (`utils.py:952`).

### 2.10 DN de groupes incohérents — ✅
Les six DN ciblent `{LDAP_OU},{LDAP_BASE_DN}` (sans re-préfixe `ou=`), PROVIDER unifié sur `providersGroup`, `group_dn = None` + garde pour ADMINISTRATOR (`utils.py:1030-1060`).

### 2.11 Validateur de mot de passe inversé — ✅
`register_form.py:36-50` : adaptateur `_validate_password` qui inverse correctement le contrat (`True` si valide, message d'erreur sinon), branché l.190 `validator = colander.Function(_validate_password)`. Vérifié empiriquement : mot de passe valide accepté, invalide → `colander.Invalid`. *(La validation reste inerte dans le parcours d'inscription tant que `form.validate` est commenté — cf. réserve 1.5 — mais le schéma est désormais correct pour tout appelant.)*

### 2.12 `get_i18n_id` : littéral `"name.lower()"` — ✅
Les **six** cas par défaut interpolent désormais réellement : `member_state_{name.lower()}` (member.py:95), `member_types_…` (:158), `role_types_…` (:216), `access_permissions_…` (permissions.py:112), `candidature_states_…` (candidature.py:86), `vote_types_…` (:128). Les tests paramétrés (`test_member.py`, `test_candidature.py`) affirment maintenant le **bon** comportement — l'ancien test qui figeait le bug a disparu.

### 2.13 Refresh SSO fragile — ✅
`home.py:44-70` : `refresh_keycloak_token` peut renvoyer `None` → déconnexion propre au lieu du `TypeError` ; le défaut piégeux `"2020-01-01T00:00:00"` a disparu (expiration absente ⇒ logout) ; le jeton **d'accès** est stocké en session (`request.session[SSO_TOKEN] = sso_token['access_token']`) au lieu d'écrire un header `Authorization` bidon dans la requête entrante. Même contrat dans `login.py:87` et `sso_login.py:113` ; `SSO_EXPIRES_AT` recalculé depuis `refresh_expires_in`. Testé (`test_views.py`). *(Nuance résiduelle assumée : le refresh a toujours lieu à chaque affichage de `home` tant que la fenêtre est valide — coût d'un aller-retour Keycloak par hit ; acceptable, à optimiser plus tard avec un seuil « ne rafraîchir que si < X min restantes ».)*

### 2.14 `Members.get_instance` singleton inter-connexions — ✅
`member.py:374-412` : quand une `connection` est fournie, le mapping est **toujours relu depuis la racine de cette connexion** et le cache re-lié ; la racine étant appelée à chaque requête, l'appel sans connexion restant (`generate_unique_oid`, member.py:738) voit le mapping de la connexion courante ; sonde de vivacité + `TypeError` explicite sinon. Docstring honnête (« Not thread safe! » — le rebind par requête rend le partage inter-threads bénin en pratique WSGI classique).

### 2.15 `ldap_factory.py` connexion globale — ✅
Le singleton `_conn` **a disparu** : chaque appel crée une connexion (le `with` des appelants la libère). Hôte/port résolus **à l'appel** (`ldap_server=None`/`ldap_port=None` par défaut, résolution l.100-104) et non plus à l'import. `reset_ldap_connection` ne gère plus que `_server`. *(Nit résiduel : `_server` reste un singleton module qui ignore des arguments différents lors d'appels ultérieurs — premier appel gagnant. Sans conséquence en prod mono-serveur ; `reset_ldap_connection()` couvre les tests.)*

### 2.16 `secret_manager.py` : `del os.environ[...]` — ✅
Six `os.environ.pop(NAME, None)` (l.32, 44-46, 48, 50). `SECRET_KEY` absent → `ValueError` explicite (vérifié empiriquement).

### 2.17 `validate_challenge` : `request.params[label]` — ✅
`register.py:375` : `request.params.get(label, '').strip()` — une réponse manquante compte comme incorrecte au lieu de lever.

### 2.18 `remind_pending_verifiers` à chaque requête — ✅
`__init__.py:50-97` : court-circuit bon marché `time.monotonic() - _reminder_last_run < interval` **avant** toute I/O, `threading.Lock` en `acquire(blocking=False)` + double-check sous verrou (pas de double-envoi concurrent), `try/except Exception` + `finally: release` (pas de 500 possible), intervalle configurable `VERIFIER_REMINDER_MIN_INTERVAL_SECONDS` (défaut 259 200 s = 72 h, `constants_and_globals.py:87`). Le drapeau d'idempotence par candidature (`verifier_reminder_sent`) complète. C'est une mitigation solide ; le déport vers une tâche planifiée (cron/celery) reste la cible long terme, plus par propreté que par nécessité.

---

## 3. Cohérence transactionnelle — ✅ traité, avec 🆕 trois nuances à acter (N4)

**Constat vérifié** : il ne reste **qu'un seul** `transaction.commit()` dans tout le code applicatif — `member.py:396`, dans `Members.get_instance`, pour matérialiser `root['members']` au premier démarrage (bootstrap justifié, conservé sciemment). Les 24 commits/aborts des six vues (`register`, `vote`, `modify_member`, `forgot_password`, `manage_provider`, `check_new_email`) ont disparu ; `pyramid_tm` **et** `pyramid_retry` sont actifs (`__init__.py:218-219`) ; l'envoi d'e-mail passe par `pyramid_mailer` transactionnel (pas de `send_immediately`) ; la garde `try/except` autour de `random_voters()` dans `prepare_for_cooperator` (`register.py:621-644`) a été **restaurée** lors du nettoyage (renvoie `voters_not_selected` sur échec LDAP au lieu de laisser remonter un 500).

Trois nuances méritent d'être **documentées comme limites connues** (aucune n'est une régression du nettoyage §3 ; les deux premières préexistaient) :

**N4.a — Les retours d'erreur committent quand même.** Les vues signalent leurs erreurs en renvoyant un dict rendu en **HTTP 200** ; or `pyramid_tm` committe toute réponse non-exception. Toute mutation ZODB faite *avant* le `return` d'erreur est donc persistée. Cas concret : `modify_member` passe `accessed_member.member_state = DATA_MODIFICATION_REQUESTED` (l.181) puis mute les champs un à un (`setattr`, l.421/425) **avant** l'unique écriture LDAP finale ; si celle-ci échoue, la vue renvoie une erreur… mais la ZODB garde les nouvelles valeurs → **divergence ZODB/LDAP** (faible gravité : `update_member_from_ldap` réaligne au prochain accès, LDAP faisant foi). *Recommandation* : sur les chemins d'erreur qui ne doivent rien persister, appeler `request.tm.doom()` avant le `return` (la transaction sera avortée sans changer le code de statut), ou restructurer pour ne muter qu'après le succès LDAP.

**N4.b — `pyramid_retry` × effets LDAP non idempotents.** Sur `ConflictError` ZODB, `pyramid_retry` **rejoue la vue entière** — y compris les effets de bord LDAP déjà réalisés. Le pire cas est `vote.py` : au rejeu, `conn.add` échoue (`entryAlreadyExists`) → la candidature n'est **pas** approuvée alors que le compte LDAP existe. Le retrait des commits intermédiaires (§3) élargit légèrement la fenêtre de conflit (transaction plus longue), sans créer le problème. *Recommandations graduées* : (1) traiter `entryAlreadyExists` comme un succès dans `register_user_to_ldap` quand le DN correspond à la candidature (idempotence) ; (2) et/ou déplacer les effets LDAP dans un hook `after_commit` du transaction manager ; (3) a minima, journaliser distinctement ce scénario pour le repérer.

**N4.c — Pas d'atomicité ZODB/LDAP.** Deux magasins, deux écritures, pas de transaction distribuée : c'est structurel. Le code embrasse déjà la bonne stratégie de réconciliation (**LDAP = source de vérité**, `update_member_from_ldap` réaligne la ZODB) ; l'écrire noir sur blanc dans la doc d'architecture (le plan `dccd0d2` s'y prête) fermera le sujet.

---

## 4. Bugs logiques de moindre gravité

### §4.14 — ✅ corrigé
`get_member_by_email` annotée et documentée (liste d'entrées LDAP, vide si aucune). *(Nit : l'annotation dans ce dump est encore `Union[Dict[str, str], None]` en l.127 alors que la docstring et le code renvoient une liste — harmoniser en `List[Entry]`.)*

### §4.1 — ⚠️ **l'audit précédent surestimait** : 2 occurrences, dont **1 seule réelle**
`grep` exhaustif : il n'y a que **deux** `(objectClass=*)` dans les `.py`, pas six :
- `__init__.py:189` — `conn.search(dn, '(objectClass=*)', search_scope='BASE')` : test d'existence d'un **DN précis** en portée BASE → **légitime**, c'est l'idiome LDAP standard, à ne pas toucher.
- `utils.py:159` — `get_ldap_member_list` : `SUBTREE` sur **toute la base** → seul vrai point ; remplacer par `(objectClass=alirpunktoPerson)` (voire `(&(objectClass=alirpunktoPerson)(employeeType=...))` quand un filtre de type est demandé) pour éviter de ramener groupes et OU puis de filtrer en Python.

### §4.18 — ⚠️ toujours une liste noire
`vote.pt:30` : `field[0] not in ['password', 'password_confirm']` — `iban` et `date_erasure_all_data` restent **exposés aux votants**. Passer à une **liste blanche** des champs pertinents pour la vérification d'identité (fullname, fullsurname, nationality, birthdate, description…).

### §4.31 — ❌ non corrigé, **et l'audit précédent pointait le mauvais fichier**
`get_majority_date` est dans **`alirpunkto/schemas/register_form.py:31-33`** (`routes.py` ne fait que 2 lignes — vue statique). Toujours `datetime.date.today() - datetime.timedelta(days=365*18)` : sur 18 ans, 4-5 années bissextiles font qu'un candidat né un 29 février ou à ~4 jours de ses 18 ans est mal classé. Correctif : `from dateutil.relativedelta import relativedelta` puis `date.today() - relativedelta(years=18)` (`python-dateutil` est déjà dans l'écosystème des dépendances Pyramid).

### Autres points §4 (4.2 → 4.35 hors ci-dessus) — non retouchés, toujours valables.

---

## 5. Qualité, style, maintenance — ❌ non corrigé (inchangé, chiffres re-mesurés)

- **Typos dans les identifiants** : `REGISTRED` (20 occurrences `.py`), `allready` (3), `Coulb` (`member.py:369`)… Les états persistés (`REGISTRED`) demandent une migration prudente — à planifier, pas à corriger à chaud.
- **`pkg_resources`** toujours importé (`__init__.py:19`) — déprécié, remplacer par `importlib.resources`.
- **`pytz`** toujours utilisé (`__init__.py:2`) — `zoneinfo` (stdlib ≥ 3.9) suffit.
- **Annotations mensongères** résiduelles : `retrieve_candidature -> Union[Candidature, Dict]` (renvoie un tuple, `utils.py:175-177`), `get_keycloak_token -> Optional[str]` (renvoie un dict, `utils.py:1624`).
- Toujours pas de `ruff`/`mypy` en CI. La suite de tests reconstruite (205) est en revanche un vrai acquis — brancher `ruff check` + `pytest` dans une CI GitHub Actions serait le meilleur ratio effort/gain de cette section.

---

## 🆕 Observations nouvelles de cette passe

### N1 — `register.pt:206` : jeton CSRF en `type="d-none"` — ⚠️ régression cosmétique toujours présente
Le 3ᵉ formulaire (vérification d'identité du coopérateur) rend `<input type="d-none" name="csrf_token" …>` — `d-none` est une classe Bootstrap, pas un type ; un type inconnu retombe sur `text`, donc le jeton **s'affiche comme champ éditable**. La protection CSRF fonctionne (le jeton est bien soumis), l'impact est purement visuel — mais c'est un champ de sécurité affiché à l'utilisateur. Les 9 autres formulaires (dont `register.pt:29` et `:85`) sont corrects. Correctif : `type="hidden"`.

### N2 — Cluster d'indexations `request.params[...]` non gardées — ⚠️ faible/modérée
Trois vues indexent directement des paramètres sous une garde qui ne teste que la présence du **bouton**, pas des champs → un POST CSRF-valide mais malformé (champ renommé/supprimé côté client, soumission scriptée) lève `KeyError` → 500 :
- `register.py:196-197` — `request.params['email']` / `['choice']` (sous `if 'submit' in request.POST`, `handle_draft_state`) ;
- `login.py:50-51` — `request.params['username']` / `['password']` (sous `if 'form.submitted'`) ;
- `forgot_password.py:187-188` — `request.params['password']` / `['password_confirm']` (branche `modify`).

Pas d'exposition de données ni de contournement — juste un 500 provocable au lieu d'un message propre. Correctif uniforme : `request.params.get('email', '')` + validation de vacuité (le même patron que 2.17). *À noter* : `modify_member` (l.286-296) est, lui, correctement gardé (`field in request.POST and …`).

### N3 — i18n : **13 clés utilisées par le code sont absentes du `.pot`** — ⚠️ à corriger avant la prochaine release
Croisement systématique des `_('…')` du code Python avec les `msgid` du `alirpunkto.pot` fourni :

**Manquantes (le `msgid` brut s'affichera)** :
| Clé | Utilisée dans |
|---|---|
| `voting_period_ended` | `vote.py:90` *(annoncée dès le correctif 2.3, jamais ajoutée)* |
| `user_not_logged_in` | `modify_member.py:99,111` ; `manage_provider.py:73` |
| `ldap_error_retry` | `modify_member.py:167` |
| `invalid_date_format` | `modify_member.py:273` |
| `must_be_administrator` | `manage_provider.py:85` |
| `accessed_member_oid_missing` | `manage_provider.py:146` |
| `provider_email_fullname_password_missing` | `manage_provider.py:95` |
| `provider_email_already_exists` | `manage_provider.py:114` |
| `provider_already_exists` / `provider_creation_failed` / `provider_created` / `provider_updated` | `manage_provider.py` (création/mise à jour) |
| `invalid_password` | `manage_provider.py` ; repli de `_validate_password` (`register_form.py:50`) |
| `error_sending_voting_result_email` | `vote.py:178` |

**Présentes** (ajoutées manuellement en fin de catalogue, l.1137-1146) : `invalid_field_value`, `provider_update_failed`, `provider_new_email_label`, `provider_new_password_label` — 4 des 5 clés annoncées ; **la 5ᵉ (`voting_period_ended`) a été oubliée**, alors même que le commit `d56f526` « synchronize translations from gettext catalogs » est passé depuis.

**Recommandation** : régénérer le `.pot` par extraction (`pot-create`/lingua sur `alirpunkto/`) plutôt que d'ajouter les clés à la main — l'oubli de `voting_period_ended` montre la limite de l'ajout manuel — puis `msgmerge` sur les `.po`. *(Hors périmètre volontaire : les noms de langues `_('Deutsch')`, `_('English')`… de `constants_and_globals.py:148+` et `_('Avatar')` de `register_form.py:87` sont aussi absents du catalogue — probablement assumé, à trancher une fois.)*

### N4 — Nuances transactionnelles — voir §3 (documentées là-bas pour rester à côté du chantier qu'elles nuancent).

---

## Points fonctionnels ouverts (hors bug, à trancher côté produit)

Repris de 2.3/2.5, toujours d'actualité dans ce dump :
1. **Égalité YES/NO refuse** la candidature (`count_yes > count_no`, `vote.py:121`) et `ABSTAIN` compte comme vote exprimé — à confirmer comme règle voulue.
2. `voter.vote` stocke le **nom** (`str`) du choix, pas un `VotingChoice` — typage à assainir (petite migration des votes en cours).
3. **Dépouillement à l'échéance non implémenté** (`@TODO` `vote.py:202`) : un vote tardif est désormais refusé (garde 2.3), mais si tous les votants n'ont pas voté avant la deadline, la candidature n'est **jamais tranchée**. Il faut dépouiller à la deadline (au prochain accès à la candidature, ou via le passage `remind_pending_verifiers`/tâche planifiée).
4. `elections_view` reste un stub (cf. 2.5).

---

## Historique des corrections (commits du 2026-07-01, complétant la table de l'audit précédent)

| Commit | Correctif | Trouvaille |
|---|---|---|
| `f5af346` · `a74e7de` | LDAP failures appliquées + mot de passe réellement changé + coercition de types | §2.7 |
| `6c4fe05` | Réparation création/mise à jour provider | §2.4 |
| `bed73b3` | Validateur de mot de passe désinversé | §2.11 |
| `a274cab` | Interpolation réelle des fallbacks `get_i18n_id` | §2.12 |
| `0f96f3c` | Nettoyage session `logout` gardé | §2.8 |
| `fd3b14a` | SSO : stockage du jeton rafraîchi + échec sans crash | §2.13 |
| `46f3fac` | `Members.get_instance` lié à la connexion passée | §2.14 |
| `b054be1` | Hôte/port LDAP résolus à l'appel, connexion SYNC non partagée | §2.15 |
| `2532bf1` | `os.environ.pop` au lieu de `del` | §2.16 |
| `e184d28` | Réponse de challenge absente = incorrecte, pas 500 | §2.17 |
| `aa74de4` · `946a65e` | Throttle + verrou + intervalle configurable des rappels | §2.18 |
| `cd9c558` · `7613940` · `4d7a045` · `5faf180` · `14ca621` · `6d43891` · `8cfbe99` · `501e3e9` | Retrait des commits explicites des 6 vues, garde `random_voters` restaurée | §3 |
| `7774ec8` · `bd28bbb` · `8763cbb` · `233313a` · `ee51deb` | Tests de non-régression (LDAP, permissions, vote, modify-member, parcours e2e) | couverture §2 |
| `d56f526` | Synchronisation des catalogues gettext | i18n *(incomplète — cf. N3)* |

---

## Reste prioritaire (ordre suggéré)

1. **1.3 — mots de passe en clair** (LDAP `hashed()` + purge/chiffrement ZODB + migration + test) : seule faille de sécurité restante, tout le reste de la section 1 est soldé.
2. **N3 — régénérer le `.pot`** et ajouter les 13 clés manquantes (dont `voting_period_ended`) + `msgmerge` des `.po` : visible par tout utilisateur dès qu'un chemin d'erreur s'affiche.
3. **N2 — garder les 6 indexations `request.params`** (patron 2.17) et **N1 — `type="hidden"`** dans `register.pt:206` : deux correctifs de dix minutes.
4. **N4.b — idempotence LDAP sous `pyramid_retry`** (traiter `entryAlreadyExists` comme succès dans `register_user_to_ldap`) et **N4.a — `request.tm.doom()`** sur les chemins d'erreur de `modify_member` : ferme les derniers angles transactionnels.
5. **Fonctionnel vote** : dépouillement à l'échéance (point 3 ci-dessus) — sans lui, une candidature avec un votant silencieux reste en limbes.
6. **§4** : liste blanche `vote.pt` (4.18), `relativedelta` (4.31, dans `register_form.py`), filtre `alirpunktoPerson` (4.1).
7. **Continu** : `ruff` + `mypy` + CI ; nits (imports morts `manage_provider`, marque pytest `functional`, clé orpheline `forget_admin_user`, annotations `retrieve_candidature`/`get_keycloak_token`/`get_member_by_email`).
