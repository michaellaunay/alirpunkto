# Revue de code — AlirPunkto — **mise à jour** (dump du 2026-06-26)

> Audit d'origine : `20260613_revue_de_code_alirpunkto.md` (dump du 2026-06-12).
> Cette version reprend chaque point et indique son état après vérification dans le dump du **2026-06-26**.
> Numéros de ligne = numérotation interne de chaque fichier dans le **nouveau** dump.
> **Révision du 2026-06-27** : intègre les correctifs appliqués *après* le dump du 2026-06-26 — **1.4** (injection de filtre LDAP), **1.6** (comparaison admin à temps constant), **1.7** (traversal de template dans `get_email`), **1.8** (énumération d'utilisateurs), **1.9** (expiration des liens via TTL Fernet), **1.10** (`decrypt_oid` qui échoue proprement), **1.11** (branding lu depuis les settings au lieu de `request.params`), **2.5** (plantage d'`elections_view`) et **§4.14** (annotation de `get_member_by_email`) sont désormais corrigés.
>
> **Révision du 2026-06-30** : refonte complète de la suite de tests (97 tests verts ; correctif de cohérence `MemberRoles.get_i18n_id` au passage), puis correctifs **2.2** (`get_access_permissions` *fail-closed* + log des cas non couverts, et lecture des candidatures pour l'administrateur), **2.1** (réactivation de la branche `voter` via comparaison sur les `oid`) et **2.3** (persistance du vote via `_p_changed`, renommage `vote_view`, lecture session robuste, vérification du retour LDAP avant approbation, et contrôle de la *deadline* de vote).

> **Révision du 2026-06-30 (suite)** : correctifs **2.9** (contrat de retour de `register_user_to_ldap` normalisé en `{'status':'error',…}`) et **2.10** (DN de groupes LDAP rendus cohérents avec la création des groupes, PROVIDER unifié sur `providersGroup`, garde anti-`NameError`).

**Légende :** ✅ corrigé · ⚠️ partiel / mitigé · ❌ non corrigé · 🆕 régression introduite depuis le 2026-06-12

## Historique des corrections (dépôt git)

Correspondance entre les commits du dépôt et les corrections d'audit, par ordre chronologique. `§` renvoie au numéro de trouvaille traité plus bas.

| Commit | Date | Correctif | Trouvaille |
|---|---|---|---|
| `05d3173` | 2026-06-13 | Chiffrement des mots de passe avant journalisation DEBUG | §1.2 |
| `f1a88a8` | 2026-06-13 | Retrait des mots de passe des attributs journalisés | §1.2 |
| `b6458c6` | 2026-06-13 | Durcissement des attributs du cookie de session | §1.1 |
| `9841a1c` | 2026-06-16 | Protection CSRF sur toutes les requêtes mutantes | §1.5 |
| `f453878` | 2026-06-27 | Échappement des entrées dans les filtres LDAP | §1.4 (CWE-90) |
| `c3d603e` | 2026-06-27 | Comparaison à temps constant des identifiants admin | §1.6 (CWE-208) |
| `0a40853` | 2026-06-27 | Validation de `email_id` contre le traversal de template | §1.7 (CWE-22) |
| `2e91661` | 2026-06-27 | Anti-énumération de comptes au reset de mot de passe | §1.8 (CWE-204) |
| `39c7406` | 2026-06-27 | Expiration des liens reset/vérification + *fail-closed* | §1.9 (CWE-613), §1.10 partiel |
| `f5ca0d3` | 2026-06-27 | Durcissement de `get_candidature_from_request` (oid invalide) | §1.10 (CWE-755) |
| `e0a9275` | 2026-06-27 | Branding lu depuis les constantes + fix plantage élections | §1.11 (CWE-601), §2.5 |
| `9e4f485` · `2832005` | 2026-06-30 | Cas `MemberRoles.NONE` dans `get_i18n_id` | §2.12 (cousin) |
| `0786e92` | 2026-06-30 | Exclusion des clés privées/certificats de l'export sources | durcissement outil |
| `278d8be` | 2026-06-30 | Reconstruction de la suite de tests (97 verts) | reconstruction tests |
| `014525b` | 2026-06-30 | Permissions *fail-closed* + lecture admin des candidatures | §2.2 |
| `d1e6d81` | 2026-06-30 | Réactivation de la branche `voter` dans `get_access_permissions` | §2.1 |
| `72848b9` | 2026-06-30 | Persistance du vote + approbation après succès LDAP | §2.3 |
| `9851714` | 2026-06-30 | Clôture du vote à l'échéance (*deadline*) | §2.3 |
| _«hash»_ | 2026-06-30 | Contrat de retour LDAP normalisé + DN de groupes cohérents | §2.9, §2.10 |

---

## Synthèse

Trois chantiers de sécurité avaient déjà été traités dans le dump du 2026-06-26 : le secret de session (1.1), les mots de passe dans les logs (1.2) et la protection CSRF (1.5). **Depuis, sept failles supplémentaires ont été corrigées** : injection de filtre LDAP (1.4), comparaison des identifiants admin (1.6), traversal de template dans `get_email` (1.7), énumération d'utilisateurs (1.8), expiration des liens (1.9), échec propre de `decrypt_oid` (1.10) et branding lu depuis les settings plutôt que `request.params` (1.11) — plus l'annotation de `get_member_by_email` (§4.14) et, côté bugs bloquants, le plantage d'`elections_view` (**2.5**, désormais corrigé mais la vue reste un *stub*). Un utilitaire `encrypt_secret_for_logs()` a été ajouté dans `secret_manager.py` et est utilisé partout où un mot de passe était auparavant journalisé en clair. **En section 1, il ne reste plus que 1.3** (mots de passe en clair LDAP/ZODB). Pour le reste — la plupart des bugs bloquants de la §2 (2.1, 2.2, 2.3, 2.5, 2.9 et 2.10 mis à part), problèmes transactionnels (§3), plupart des bugs mineurs (§4) et dette de qualité (§5) — rien n'a bougé. Côté §2, **2.5** (plantage d'`elections_view`, mais la vue reste un *stub*), **2.2** (`get_access_permissions` rendu *fail-closed* + lecture admin des candidatures), **2.1** (branche `voter` réactivée) **2.3** (persistance du vote + robustesse de `vote_view`) puis **2.9/2.10** (contrat de retour et DN de groupes LDAP) ont été traités. Au passage, une petite régression a été introduite dans `register.pt` et le bug 2.12 subsiste (cousin corrigé sur `MemberRoles`).

| Section | Corrigé | Partiel | Non corrigé |
|---|---|---|---|
| 1. Sécurité critique | 1.1, 1.2, **1.4**, 1.5, **1.6**, **1.7**, **1.8**, **1.9**, **1.10**, **1.11** | — | 1.3 |
| 2. Bugs bloquants | **2.1**, **2.2**, **2.3**, **2.5**, **2.9**, **2.10** | 2.15, 2.18 | 2.4, 2.6–2.8, 2.11–2.14, 2.16, 2.17 |
| 3. Transactions | — | — | tout |
| 4. Bugs mineurs | **§4.14** | §4.18 | §4.1, §4.31, … (inchangés) |
| 5. Qualité | — | — | typos, pkg_resources, pytz, types… |

---

## 1. Failles de sécurité critiques

### 1.1 Cookie de session signé avec une constante publique — ✅ **corrigé**
`__init__.py` l.184 : `hash_object.update(get_secret(SECRET_KEY).encode('utf-8'))` — la **valeur** du secret est désormais utilisée. La fabrique pose aussi `httponly=True, secure=True, samesite='Lax'` (l.185). Conforme à la correction proposée.

### 1.2 Mots de passe en clair dans les logs — ✅ **corrigé**
Nouvel utilitaire `encrypt_secret_for_logs()` (`secret_manager.py` l.59). Appliqué :
- `views/login.py` l.125 : `…with {encrypt_secret_for_logs(password)=}` ;
- `views/forgot_password.py` l.221 : idem, + un `log.info` sans mot de passe ;
- `utils.py::register_user_to_ldap` l.987-988 : `safe_attributes` retire `userPassword` du dict avant log, et le mot de passe explicite est chiffré.

### 1.3 Mots de passe stockés en clair — ❌ **non corrigé**
- **LDAP** : `register_user_to_ldap` l.931 envoie toujours `'userPassword': password` en clair ; `update_member_password` l.1055 fait `MODIFY_REPLACE` avec le mot de passe brut. Aucun `hashed()` ni `modify_password` dans le code (seuls les comptes bootstrap du LDIF sont pré-hachés `{SSHA}`).
- **ZODB** : `register.py` l.534-535 recopie toujours tous les champs de `request.params` correspondant à `MemberDatas.__dataclass_fields__` (dont `password`/`password_confirm`), et aucun `del data.password` n'a été ajouté après création LDAP. Le mot de passe du candidat reste en clair dans la base.

### 1.4 Injection de filtre LDAP — ✅ **corrigé** (post-dump, 2026-06-27)
`escape_filter_chars` (de `ldap3.utils.conv`) enveloppe désormais chaque valeur contrôlée par l'utilisateur dans les cinq filtres concernés :
- `utils.py::get_member_by_email` : `f'(mail={escape_filter_chars(email.strip())})'` ;
- `utils.py::is_valid_unique_pseudonym` : `f"(cn={escape_filter_chars(pseudonym)})"` ;
- `utils.py::update_member_from_ldap` : `f'(uid={escape_filter_chars(oid)})'` ;
- `utils.py::get_oid_from_pseudonym` : `f'(cn={escape_filter_chars(pseudonym)})'` ;
- `views/login.py::check_password` : `f'(uid={escape_filter_chars(oid)})'`.

Les filtres statiques (`(objectClass=*)`, `(&(employeeType=cooperator)…)`) n'ont pas d'entrée utilisateur et restent inchangés. L'import mort `get_ldap_server` a été retiré de `utils.py` au passage.

### 1.5 CSRF non vérifié — ✅ **corrigé**
- `__init__.py` l.187 : `config.set_default_csrf_options(require_csrf=True)` — protection globale active sur tous les POST.
- Tous les formulaires manuels portent désormais le jeton : `login.pt`, `forgot_password.pt`, `manage_provider.pt`, `modify_member.pt`, `register.pt`, `vote.pt`, etc.
- *Reste secondaire* : `register.py` l.470 garde `#form.validate(items)` commenté (validation de schéma colander toujours absente), mais ce n'est plus le mécanisme de protection CSRF. Voir aussi 🆕 ci-dessous (`register.pt`).

### 1.6 Comparaison de mot de passe admin non constante — ✅ **corrigé** (post-dump, 2026-06-27)
`utils.py::is_admin` compare désormais identifiant et mot de passe via `hmac.compare_digest` (à temps constant) sur leurs octets UTF-8 :
- plus de comparaison `==` court-circuitante → fuite temporelle fermée ;
- encodage en `utf-8` (le mode `str` de `compare_digest` n'accepte que l'ASCII et lèverait `TypeError`) ;
- `.strip()` retiré du mot de passe (les espaces en bordure sont à nouveau significatifs ; conservé sur l'identifiant, sans risque) ;
- les deux comparaisons sont évaluées avant d'être combinées, donc le résultat sur l'identifiant ne fuit pas non plus par le timing.

Import `hmac` ajouté.

### 1.7 `get_email` : anti-injection illusoire + rendu piloté par l'URL — ✅ **corrigé** (post-dump, 2026-06-27)
- **Traversal fermé** : `email_id` est désormais validé par `VALID_EMAIL_ID = re.compile(r'[a-z0-9_]+')` via `fullmatch` avant de construire `f"{email_id}.pt"`. Plus de `/`, `\` ni `.` possibles → impossible de sortir de `LC_MESSAGES`.
- **Liste noire supprimée** : le test `"python" in value` + `eval(|exec(|__import__` est retiré. Il ne protégeait de rien (les valeurs de `request.params` sont passées au moteur ZPT comme données, pas comme source de template) et rejetait des entrées légitimes contenant « python ».
- **Variables de template** : déjà restreintes à `expected_variables ∩ params` (inchangé).

### 1.8 Énumération d'utilisateurs — ✅ **corrigé** (post-dump, 2026-06-27)
Les cinq points de sortie de l'étape `'submit'` de `forgot_password.py` (adresse inconnue, compte admin, échec de chargement LDAP, succès, échec d'envoi) renvoient désormais un dict **strictement identique** : `{"message": _('forget_email_sent'), "member": None, "form": None}`. Le template rend donc la même page dans tous les cas — y compris la visibilité du formulaire, qui dépend de `not member`. L'e-mail n'est envoyé que si le compte existe ; les autres cas sont journalisés côté serveur.

> **⚠️ Suivi requis** : `forget_email_sent` est maintenant affiché même sans compte correspondant. Son libellé doit rester **neutre** (« *si* un compte existe, un lien a été envoyé ») et ne pas affirmer qu'un e-mail a réellement été envoyé. Voir la section *Suivi* en fin de document.
>
> **Limite résiduelle (timing)** : le chemin « compte existe » reste plus lent (lectures LDAP, `commit`, envoi) → énumération possible par le temps de réponse. Chantier séparé (envoi en tâche de fond).

### 1.9 Liens de réinitialisation sans expiration — ✅ **corrigé** (post-dump, 2026-06-27)
`decrypt_oid` passe désormais un `ttl` à `fernet.decrypt(decoded, ttl=ttl)`. Le jeton Fernet étant horodaté à la création (`encrypt_oid`), tout lien plus vieux que le TTL est rejeté. Le délai est porté par une nouvelle constante `OID_LINK_TTL_SECONDS` (24 h par défaut, surchargée par la variable d'env `ALIRPUNKTO_OID_LINK_TTL_SECONDS`), lue **à chaque appel** (paramètre `ttl=None` puis lecture dans le corps → pas de défaut gelé, surchargeable par appel et testable par monkeypatch).

### 1.10 `decrypt_oid` lève au lieu de retourner `None` — ✅ **corrigé** (post-dump, 2026-06-27)
`decrypt_oid` enveloppe désormais décodage et déchiffrement dans un `try/except (InvalidToken, ValueError, TypeError)` et renvoie `(None, None)` sur tout jeton invalide, malformé ou expiré (`Fernet(secret)` reste hors du `try` pour qu'une clé mal configurée remonte). Ce contrat correspond à ce que les appelants attendaient déjà : la branche `is None` de `check_new_email` (jusque-là inatteignable) devient active, et `retrieve_candidature` comme `forgot_password._retrieve_member` testent déjà `None` → un `?oid` forgé/expiré affiche une page propre au lieu d'un 500. Le seul appelant non gardé, `get_candidature_from_request` (qui était du **code mort**), a été durci : tous ses modes d'échec renvoient `None`, et le `raise Exception("Seed mismatch")` générique a été supprimé.

### 1.11 `site_name` / `domain_name` pris dans la requête — ✅ **corrigé** (post-dump, 2026-06-27)
Les trois vues qui lisaient ces valeurs depuis `request.params` — `login_view`, `sso_login.callback_view` et `elections_view` — lisent désormais les constantes de confiance `SITE_NAME` / `DOMAIN_NAME` / `ORGANIZATION_DETAILS`. Plus aucune lecture de ces clés depuis `request.params` : le vecteur de spoofing/phishing est fermé. Les constantes reçoivent des valeurs par défaut (corrige au passage les e-mails qui affichaient `None`). La clé d'env `organization_details` est normalisée en `ORGANIZATION_DETAILS` (voir *Suivi* pour la réserve de déploiement). À noter : les lectures `request.registry.settings.get('site_name'…)` présentes dans d'autres vues sont une source distincte et **de confiance** (config serveur), hors périmètre.

---

## 2. Bugs bloquants — **aucun corrigé** (2 partiellement mitigés)

### 2.1 Vérificateurs sans permissions — ✅ **corrigé** (post-dump, 2026-06-30)
La branche `voter` de `get_access_permissions` testait `accessor.oid in accessed.voters` — une `str` comparée à une liste de `Voter` (dataclass), donc **toujours `False`** : branche morte, le votant tombait dans la branche générique et, depuis 2.2, recevait `NO_MEMBER_PERMISSIONS` (refus). Corrigé en `accessor.oid in {voter.oid for voter in accessed.voters}`. Vérifié empiriquement : un votant obtient désormais `access['voter'][état]` pour les sept états de candidature (sans warning), tandis qu'un non-votant reste refusé et tracé (comportement 2.2 inchangé).

### 2.2 `KeyError` sur de nombreux couples (rôle, état) — ✅ **corrigé** (post-dump, 2026-06-30)
`get_access_permissions` faisait cinq accès par indexation directe `access[…][…]`, exposés au `KeyError`/500. Ils passent désormais par un helper `_resolve_permissions(externe, interne)` qui : renvoie la cellule si le couple existe ; sinon **logue un `warning`** identifiant le couple manquant et renvoie le repli *deny-all* `NO_MEMBER_PERMISSIONS` (tous champs `Permissions.NONE`). Double bénéfice : *fail-closed* (un trou refuse au lieu de planter) **et** visibilité — toute non-couverture est tracée pour un débogage immédiat. Vérifié empiriquement : clé présente → objet identique (`is`) à l'ancien accès, sans warning ; clé absente → `NO_MEMBER_PERMISSIONS` + un warning.

En complément, la matrice a été **étoffée pour l'administrateur** : un nouveau profil `ADMIN_CANDIDATURE_PERMISSIONS` (lecture seule sur tous les champs de candidature ; les champs hérités du membre réutilisent la politique `ADMIN_MEMBER_PERMISSIONS`, donc IBAN masqué et `seed` non lisible) est branché sur `access['Administrator']` pour les sept états de candidature. Un administrateur peut donc consulter une candidature en cours (les 28 plantages côté non-propriétaire sont remplacés par une lecture pour l'admin, un refus tracé pour les autres rôles). Les trous restants (combinaisons `Owner` non rencontrées dans le parcours d'inscription, accès `Ordinary`/`Cooperator`/`Provider` à une candidature) renvoient un refus journalisé — voir *Suivi*.

### 2.3 Vote probablement jamais persisté — ✅ **corrigé** (post-dump, 2026-06-30)
Quatre points traités dans `vote.py` : (1) **persistance** — `voter.vote = vote` mute un `Voter` (dataclass) niché dans la liste `_voters` d'une `Candidature` persistante sans la marquer *dirty* ; ajout de `candidature._p_changed = True` juste après. **Prouvé en vraie ZODB** (`FileStorage` rouvert) : sans le flag le vote relu vaut `None` (perdu), avec le flag il est bien persisté. (2) **renommage** de la vue `login_view` → `vote_view` (copier-coller) ; (3) lecture session `request.session['site_name'/...]` → `.get(..., SITE_NAME/DOMAIN_NAME/ORGANIZATION_DETAILS)`, plus de `KeyError` (cohérent avec 1.11) ; (4) **résultat de `register_user_to_ldap` vérifié** — l'approbation n'est faite que si le retour vaut `{'status': 'success'}` (test défensif `isinstance(...) and .get('status')=='success'`, robuste à l'incohérence de contrat 2.9) ; sinon log d'erreur, `abort()` et message à l'utilisateur, la candidature ne passe **plus** `APPROVED` sur échec LDAP. Vérifié en pilotant `vote_view` (échec → reste `PENDING` + vote conservé ; succès → `APPROVED` ; retour non-dict → reste `PENDING`). Suite complète 97/97. **Contrôle de la *deadline* de vote ensuite implémenté** (post-dump, 2026-06-30) : si `candidature.verification_deadline` est dépassée, `vote_view` renvoie une erreur `voting_period_ended` et le template masque le formulaire (deadline absente ⇒ pas de blocage ; *deadline naive* normalisée en UTC) — vérifié sur 5 cas. Points fonctionnels restants (voir *Suivi*) : sémantique d'égalité YES/NO, typage `str` vs `VotingChoice`, calcul du résultat à l'échéance, et ajout de la clé i18n.

### 2.4 `manage_provider.py` branche « update » cassée — ❌ **non corrigé**
Inchangée : `RegisterForm(request, schema=…, member=…)` l.159 (constructeur inexistant), `form.validate`/`form.get_data` l.162-163, `is_valid_email(data['email'])` sans `request` l.164, `update_ldap_member(request, member, data)` (3ᵉ arg = liste, pas dict) l.168, `send_member_state_change_email(member, MemberStates.ACTIVE, request)` (signature inversée + état inexistant) l.169, `provider_email in providers` l.109, `manage_provider_schema` dict mort l.44. *(La branche « create » corrige en revanche l'appel `is_valid_email(provider_email, request)` l.96.)*

### 2.5 `elections.py` plantage garanti — ✅ **corrigé** (post-dump, 2026-06-27)
`get_candidatures(request)` reçoit désormais l'argument `request` → plus de `TypeError`/500 pour un utilisateur connecté. **Réserve** : la vue reste un *stub* — elle renvoie toujours `{"elections": []}`, le résultat `candidatures` est assigné mais inutilisé (F841), et `logged_in`/`username` sont encore lus depuis `request.params`. La logique de filtrage des élections est à écrire (TODO posés). Voir *Suivi*.

### 2.6 `update_ldap_member` mapping incohérent — ❌ **non corrigé**
l.1069-1075 : la valeur par défaut de `fields_to_update` liste toujours des noms LDAP (`sn`, `gn`, `IBAN`, `uniqueMemberOf`, `employeeType`, `dateErasureAllData`…) alors que le corps teste des noms modèle (`fullname`, `lang1`, `iban`…). l.1101 teste `'data.fullsurname'` (la vue pousse `fullsurname`). l.1138 `member.data.uniqueMemberOf` et l.1140 `member.data.dateErasureAllData` → `AttributeError`. Argument par défaut mutable et `MODIFY_DELETE` sur attribut absent toujours présents.

### 2.7 `modify_member.py` retour mal interprété + mot de passe inopérant — ❌ **non corrigé**
l.374 : toujours `if not sending_success` alors que `update_ldap_member` renvoie toujours un dict (truthy) → erreur LDAP traitée comme succès. Branche mot de passe : `is_valid_password` appelé l.346 mais `update_member_password` jamais invoqué → changement sans effet. `#@TODO cast the value to the right type` toujours là (l.348). `email_template = "reset_password_email"` pour un changement d'email l.285.

### 2.8 `logout` : `KeyError` sur `?username=` — ❌ **non corrigé**
`utils.py` l.1548-1550 : toujours `del request.session['username']` (clé jamais posée). `pop('username', None)` non appliqué.

### 2.9 `register_user_to_ldap` contrat de retour incohérent — ✅ **corrigé** (post-dump, 2026-06-30)
Le chemin « pseudonyme invalide » retournait tel quel le `{'error': …}` de `is_valid_unique_pseudonym` (sans clé `status`), alors que les appelants lisent `result['status']` (et `register.py` lit aussi `result['message']`) → `KeyError`. Normalisé en `{'status': 'error', 'message': error.get('error'), **error}` : on respecte le contrat des autres retours de la fonction tout en conservant `error`/`error_details`. Vérifié en exécutant la fonction avec un pseudonyme invalide → `{'status':'error','message':…,'error_details':…}`.

### 2.10 DN de groupes incohérents — ✅ **corrigé** (post-dump, 2026-06-30)
Trois points : (a) le `uniqueMemberOf` d'un PROVIDER pointait `providerMembersGroup` alors que le groupe créé/modifié est `providersGroup` → unifié sur `providersGroup` ; (b) les six DN de groupes re-préfixaient `ou={LDAP_OU}` alors que la création des groupes (`__init__.py` l.159-160) et le DN utilisateur emploient `{LDAP_OU}` directement → préfixe `ou=` retiré, les DN ciblent désormais l'endroit où les groupes existent réellement ; (c) `group_dn` n'était pas défini pour ADMINISTRATOR/`_` → `NameError` potentiel dans le log final, corrigé par `group_dn = None` + garde `if group_dn is not None`. Vérifié en exécutant `register_user_to_ldap` avec une connexion LDAP mockée : pour COOPERATOR/ORDINARY/PROVIDER le DN passé à `conn.modify` est **identique** à celui que crée `__init__.py`, et `uniqueMemberOf` pointe le même DN ; ADMINISTRATOR ne fait aucun `modify` et ne lève pas.

### 2.11 Validateur de mot de passe inversé — ❌ **non corrigé**
`schemas/register_form.py` l.173 : toujours `validator = colander.Function(is_valid_password)` (logique inversée). Inoffensif uniquement parce que `form.validate` reste commenté.

### 2.12 `get_i18n_id` : `return(f"name.lower()")` — ❌ **non corrigé** (et 🆕 figé par les tests)
Toujours la chaîne littérale au cas par défaut : `member.py` l.86 et l.157, `permissions.py` l.112 (et le doublon `member.py` l.94). 🆕 Les nouveaux tests `tests/test_views.py` l.20 et l.57 **affirment** ce comportement bogué (`== "name.lower()"`) : corriger le test en même temps que le code.

### 2.13 Refresh SSO fragile — ❌ **non corrigé**
`home.py` : `refresh_keycloak_token` peut renvoyer `None` → `sso_token['access_token']` l.51 `TypeError` ; `request.headers['Authorization'] = f'Bearer {sso_token}'` l.55 (écrit dans la requête entrante, et `sso_token` est un dict) ; défaut `"2020-01-01T00:00:00"` l.46 → déconnexion immédiate ; rafraîchissement à chaque affichage. Mêmes bugs dans `login.py` l.78-79.

### 2.14 `Members.get_instance` singleton ZODB inter-connexions — ❌ **non corrigé**
`member.py` l.368 `_instance = None`, mise en cache l.404, test de vivacité `'test' in Members._instance` l.386, et `Members.get_instance()` appelé sans connexion l.722. Risque de `ConnectionStateError`/lectures périmées intact.

### 2.15 `ldap_factory.py` connexion globale — ⚠️ **partiel**
Ajout d'un `reset_ldap_connection()` et création d'une connexion **neuve pour les stratégies ≠ SYNC** (utile en test). Mais pour la stratégie **SYNC de production**, `_conn` reste un singleton module-level (l.135-151) → non thread-safe ; les arguments par défaut `server_name=get_ldap_server_name()` (l.34) sont toujours évalués à l'import. Le problème de fond demeure.

### 2.16 `secret_manager.py` : `del os.environ[...]` non protégé — ❌ **non corrigé**
l.32/44-46/48/50 : toujours `del os.environ[...]` (lève `KeyError` avant le `ValueError` prévu) au lieu de `os.environ.pop(name, None)`.

### 2.17 `validate_challenge` : `request.params[label]` → `KeyError` — ❌ **non corrigé**
`register.py` l.401 : toujours `request.params[label].strip()`. `.get(label, '')` non appliqué.

### 2.18 `remind_pending_verifiers` sur chaque requête — ⚠️ **partiel**
Toujours abonné à `NewRequest` (`__init__.py` l.66). Mitigations ajoutées : court-circuit `if PYTEST_CURRENT_TEST`, `try/except`, et un drapeau d'idempotence `verifier_reminder_sent` (+ `verifier_reminder_sent_at`) dans `send_verifier_reminder_emails` (l.820, 895-896). Mais toujours O(n) par requête, sans verrou (double-envoi concurrent possible) et non déplacé vers une tâche planifiée.

---

## 3. Cohérence transactionnelle — ❌ **non corrigé**
25 appels explicites `transaction.commit()` subsistent (notamment `forgot_password.py`, `modify_member.py`, `register.py`, `vote.py`), toujours combinés à `pyramid_tm`. Aucune stratégie unique adoptée.

---

## 4. Bugs logiques de moindre gravité (points vérifiés)
- **§4.14** ✅ **corrigé** (post-dump) : `get_member_by_email` est désormais annoté `-> List[Entry]` et sa docstring décrit le retour réel (liste d'entrées LDAP, vide si aucune).
- **§4.1** ❌ `(objectClass=*)` toujours présent (6 occurrences, dont `get_ldap_member_list` l.155 et démarrage).
- **§4.18** ⚠️ `vote.pt` filtre désormais `password` **et** `password_confirm` (l.30), mais reste une **liste noire** : `iban` et `date_erasure_all_data` sont toujours exposés aux votants. Passer à une liste blanche.
- **§4.31** ❌ `get_majority_date` (`routes.py` l.33) : toujours `timedelta(days=365*18)` au lieu de `relativedelta(years=18)`.
- Les autres points (§4.2 à §4.35, hors §4.14) n'ont pas été retouchés ; ils restent valables.

---

## 5. Qualité, style, maintenance — ❌ **non corrigé**
- **Typos** toujours présentes, y compris dans des identifiants : `REGISTRED` (≈23×), `allready` (≈3×), `Coulb` (`member.py` l.366)…
- **`pkg_resources`** toujours importé (`__init__.py` l.19, `resource_filename` l.278-279) — déprécié.
- **`pytz`** toujours utilisé.
- **Annotations de type** encore largement mensongères (`retrieve_candidature -> Union[Candidature, Dict]` mais renvoie un tuple, `get_keycloak_token -> Optional[str]` mais renvoie un dict, etc.) ; `get_member_by_email` a en revanche été corrigée (§4.14).
- Pas de `ruff`/`mypy`/tests fonctionnels par vue ajoutés.

---

## 🆕 Régressions / points introduits depuis le 2026-06-12
1. **`register.pt` l.207** : le jeton CSRF est rendu avec `<input type="d-none" …>` au lieu de `type="hidden"`. Un type inconnu retombe sur `text` → le champ (et le jeton) s'affiche comme une zone de texte éditable. Les 9 autres formulaires utilisent correctement `type="hidden"`.
2. **`tests/test_views.py` l.20 et l.57** : tests qui valident le comportement bogué de `get_i18n_id` (`"name.lower()"`). Ils « passent » mais verrouillent le bug 2.12 — à corriger conjointement.

---

## Suivi — dette laissée par les correctifs (à ne pas oublier)
- **1.8 — libellé neutre (requis)** : `forget_email_sent` est désormais affiché même lorsqu'aucun compte ne correspond. Reformuler la chaîne i18n (fr **et** en) en message neutre — p. ex. « Si un compte est associé à cette adresse, un lien de réinitialisation vient d'être envoyé. » — et **ne pas** affirmer qu'un e-mail a été envoyé. Sans ça, l'énumération reste fermée mais le message ment à l'utilisateur légitime.
- **1.8 — clé i18n orpheline (nit facultatif)** : `forget_admin_user` n'est plus référencé après le correctif → la supprimer des `.po`/`.pot`. (`forget_email_in_member_list` et `forget_email_send_error` peuvent encore servir ailleurs : vérifier avant de retirer.)
- **1.8 — canal temporel (hors périmètre)** : égaliser le temps de réponse entre « compte existe » et « compte inconnu » (envoi d'e-mail en tâche de fond) pour fermer l'énumération par timing.
- **1.7 — nit facultatif** : dans `get_email.extract_zpt_variables`, remplacer le `print(f"File not found…")` par un `log.warning`.
- **1.9 — nettoyage** : supprimer le `@TODO check the validity period` désormais obsolète dans `forgot_password.py` (l.83), et envisager un TTL plus court par appel pour le reset de mot de passe (p. ex. `decrypt_oid(..., ttl=3600)`) que pour la validation d'e-mail.
- **1.10 — nit PEP 8** : le durcissement de `get_candidature_from_request` a laissé une seule ligne vide avant `generate_key` au lieu de deux (E302) — à restaurer pour un lint propre.
- **1.11 — déploiement** : la clé d'env a été normalisée en `ORGANIZATION_DETAILS` (majuscules). Rien dans le dépôt ne définissait la version minuscule, mais un `.env`/docker-compose non versionné qui poserait `organization_details` doit être renommé. (Le réglage `.ini` `organization_details` lu via `registry.settings` est distinct et inchangé.)
- **2.5 — vue à compléter** : `elections_view` ne plante plus mais reste un *stub* — `candidatures` assigné/inutilisé (F841), `logged_in`/`username` encore lus depuis `request.params`, et la logique de filtrage des élections (TODO) à implémenter.
- **2.2 — matrice `access` : couverture restante** : l'administrateur lit désormais les candidatures (profil `ADMIN_CANDIDATURE_PERMISSIONS`). Restent **non couverts et donc refusés** (chaque refus est tracé par un `warning`, ce qui facilite le diagnostic) : l'accès d'un `Ordinary`/`Cooperator`/`Provider` à une candidature, et les combinaisons `(candidature_state, type)` du propriétaire qui ne surviennent pas dans le parcours d'inscription. Le parcours d'inscription normal du propriétaire **est** couvert. Si d'autres rôles doivent voir les candidatures, ajouter les cellules correspondantes (chantier fonctionnel, distinct de la sécurisation 2.2).
- **2.3 — points de `vote.py`** : ✅ contrôle de *deadline* désormais implémenté. Restent : (a) une **égalité YES/NO refuse** la candidature (`count_yes > count_no` requis) et `ABSTAIN` compte comme vote exprimé — à confirmer fonctionnellement ; (b) `voter.vote` stocke le **nom** (`str`) au lieu d'un `VotingChoice` — à typer proprement ; (c) **calcul du résultat à l'échéance** (@TODO l.153 « if date is passed, compute the result with the votes ») non fait : un vote arrivé après la deadline est désormais refusé, mais si tous les votants n'ont pas voté avant l'échéance, la candidature n'est jamais tranchée — il faudra dépouiller à la deadline (tâche planifiée / au prochain accès). Enfin, **ajouter la clé i18n `voting_period_ended`** aux catalogues `fr`/`en` (sinon le `msgid` brut s'affiche).

---

## Reste prioritaire (ordre suggéré)
1. **Faille de sécurité restante** : **1.3** seul subsiste en section 1 (hachage LDAP + purge `data.password`).
2. **Bugs bloquants §2** : 2.1, 2.2, 2.3, 2.5, 2.9 et 2.10 faits — continuer par 2.6/2.7 (mapping et retour `update_ldap_member`), 2.4 (`manage_provider`), 2.11 (validateur de mot de passe), 2.12 (+ test), 2.13 (SSO).
3. **Robustesse** : §3 stratégie transactionnelle, 2.14/2.15 singletons, 2.18 hors cycle requête.
4. **Continu** : `ruff` + `mypy` + tests par vue ; corriger la régression `register.pt` et le test qui fige 2.12.
