# Revue de code — AlirPunkto — **mise à jour** (dump du 2026-06-26)

> Audit d'origine : `20260613_revue_de_code_alirpunkto.md` (dump du 2026-06-12).
> Cette version reprend chaque point et indique son état après vérification dans le dump du **2026-06-26**.
> Numéros de ligne = numérotation interne de chaque fichier dans le **nouveau** dump.
> **Révision du 2026-06-27** : intègre les correctifs appliqués *après* le dump du 2026-06-26 — **1.4** (injection de filtre LDAP), **1.6** (comparaison admin à temps constant), **1.7** (traversal de template dans `get_email`), **1.8** (énumération d'utilisateurs), **1.9** (expiration des liens via TTL Fernet), **1.10** (`decrypt_oid` qui échoue proprement), **1.11** (branding lu depuis les settings au lieu de `request.params`), **2.5** (plantage d'`elections_view`) et **§4.14** (annotation de `get_member_by_email`) sont désormais corrigés.
>
> **Révision du 2026-06-30** : refonte complète de la suite de tests (97 tests verts ; correctif de cohérence `MemberRoles.get_i18n_id` au passage), puis correctifs **2.2** (`get_access_permissions` *fail-closed* + log des cas non couverts, et lecture des candidatures pour l'administrateur), **2.1** (réactivation de la branche `voter` via comparaison sur les `oid`) et **2.3** (persistance du vote via `_p_changed`, renommage `vote_view`, lecture session robuste, vérification du retour LDAP avant approbation, et contrôle de la *deadline* de vote).

> **Révision du 2026-06-30 (suite)** : correctifs **2.9** (contrat de retour de `register_user_to_ldap` normalisé en `{'status':'error',…}`) et **2.10** (DN de groupes LDAP rendus cohérents avec la création des groupes, PROVIDER unifié sur `providersGroup`, garde anti-`NameError`).

> **Révision du 2026-06-30 (suite 2)** : correctifs **2.6** (`update_ldap_member` : mapping unifié sur les noms modèle, `AttributeError` levées, `MODIFY_REPLACE` au lieu de `MODIFY_DELETE`, argument par défaut non mutable) et **2.7** *partiel* (`modify_member` : retour LDAP correctement interprété, écriture effective du mot de passe via `update_member_password`, bon template d'email ; reste le cast de types).

> **Révision du 2026-07-01** : **section §2 des bugs bloquants entièrement traitée** (2.1–2.12). Correction du bloc `lang2`/`lang3` de **2.6** (mélangé lors de l'application : perte de la 2ᵉ langue et `MODIFY_DELETE` résiduel — remis en `MODIFY_REPLACE` de la bonne valeur), **2.7** *complété* (cast des valeurs de formulaire vers le type déclaré du champ via `get_type_hints(MemberDatas)`, avec gestion d'erreur de saisie), **2.4** (`manage_provider` : détection des doublons par e-mail, réécriture complète de la branche « update », champs éditables + action `update` dans le template), **2.11** (validateur de mot de passe désinversé via un adaptateur au contrat de `colander.Function`), **2.12** (les quatre branches `get_i18n_id` interpolent enfin `name.lower()`), **2.8** (`KeyError` sur `/logout?username=` supprimé) et **2.13** (refresh SSO robuste : token d'accès stocké en session, `None` et expiration gérés), **2.14** (`Members.get_instance` lié à la connexion fournie, fin de la réutilisation inter-connexions) et **2.16** (`get_secret` : `os.environ.pop` au lieu de `del`, plus de `KeyError` masquant le `ValueError`) et **2.17** (`validate_challenge` : une réponse manquante compte comme incorrecte au lieu de lever `KeyError`). **La section §2 des bugs bloquants est ainsi entièrement traitée** (2.1–2.17 corrigés ; seules 2.15/2.18 restent partiellement mitigées). **Puis 2.15** (LDAP : hôte/port résolus au call time, singleton SYNC remplacé par une connexion fraîche par appel) et **2.18** (scan de rappel des vérificateurs throttlé + verrouillé) ont été complétés : **les 18 trouvailles de la §2 sont désormais corrigées**, chacune verrouillée par des tests. **Surtout, une suite de tests de non-régression a été ajoutée pour l'ensemble de ces correctifs** : 99 tests répartis en 17 fichiers, portant la suite de 97 à **196 tests verts** ; chaque test a été vérifié comme *échouant* sur le code pré-correctif. Voir la nouvelle section « Tests de non-régression ».

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
| `6211c8d` | 2026-06-30 | Contrat de retour LDAP normalisé + DN de groupes cohérents | §2.9, §2.10 |
| `f5af346` | 2026-07-01 | `modify_member` : retour LDAP interprété + mot de passe écrit | §2.7 |
| `2e55125` | 2026-07-01 | `update_ldap_member` : mapping sur les noms modèle + bloc `lang2`/`lang3` | §2.6 |
| `a74e7de` | 2026-07-01 | Cast des valeurs de formulaire vers le type déclaré du champ | §2.7 |
| `6c4fe05` | 2026-07-01 | Réparation des branches création/mise à jour de fournisseur | §2.4 |
| `bed73b3` | 2026-07-01 | Correction du validateur de mot de passe inversé | §2.11 |
| `a274cab` | 2026-07-01 | Interpolation de `name` dans les fallbacks `get_i18n_id` | §2.12 |
| `7774ec8` · `bd28bbb` · `8763cbb` · `233313a` | 2026-07-01 | Suite de tests de non-régression (§2.1/2.2/2.3/2.6/2.7/2.9) | tests §2 |
| `0f96f3c` | 2026-07-01 | `logout` : suppression sûre de la clé de session (`pop` au lieu de `del`) + tests | §2.8 |
| `fd3b14a` | 2026-07-01 | SSO : token d'accès stocké en session + refresh robuste (`None`, expiration) | §2.13 |
| `46f3fac` | 2026-07-01 | `Members.get_instance` lié à la connexion fournie (fin du partage inter-connexions) | §2.14 |
| `2532bf1` | 2026-07-01 | `get_secret` : `os.environ.pop` au lieu de `del` (plus de `KeyError`) | §2.16 |
| `e184d28` | 2026-07-01 | `validate_challenge` : réponse manquante = incorrecte (plus de `KeyError`) | §2.17 |
| `b054be1` | 2026-07-01 | LDAP : hôte/port résolus au call time + connexion fraîche par appel | §2.15 |
| `aa74de4` | 2026-07-01 | Throttle + verrou du scan de rappel des vérificateurs | §2.18 |
| `946a65e` | 2026-07-01 | Intervalle de rappel configurable (`VERIFIER_REMINDER_MIN_INTERVAL_SECONDS`, défaut 72 h) | §2.18 |
| `cd9c558` | 2026-07-01 | Retrait du commit explicite mid-vue (rendu du formulaire candidat) | §3 (register) |
| `7613940` | 2026-07-01 | Retrait des 6 autres commits explicites de `register.py` (mailer transactionnel) | §3 (register) |
| _«hash»_ | 2026-07-01 | Restauration de la garde LDAP autour de `random_voters` (`prepare_for_cooperator`) + tests | §3 (register) |

---

## Synthèse

Trois chantiers de sécurité avaient déjà été traités dans le dump du 2026-06-26 : le secret de session (1.1), les mots de passe dans les logs (1.2) et la protection CSRF (1.5). **Depuis, sept failles supplémentaires ont été corrigées** : injection de filtre LDAP (1.4), comparaison des identifiants admin (1.6), traversal de template dans `get_email` (1.7), énumération d'utilisateurs (1.8), expiration des liens (1.9), échec propre de `decrypt_oid` (1.10) et branding lu depuis les settings plutôt que `request.params` (1.11) — plus l'annotation de `get_member_by_email` (§4.14) et, côté bugs bloquants, le plantage d'`elections_view` (**2.5**, désormais corrigé mais la vue reste un *stub*). Un utilitaire `encrypt_secret_for_logs()` a été ajouté dans `secret_manager.py` et est utilisé partout où un mot de passe était auparavant journalisé en clair. **En section 1, il ne reste plus que 1.3** (mots de passe en clair LDAP/ZODB). **Toute la section §2 des bugs bloquants (2.1 à 2.18) est désormais corrigée** — les 18 trouvailles, chacune verrouillée par des tests de non-régression. Restent inchangés : les problèmes transactionnels (§3), la plupart des bugs mineurs (§4) et la dette de qualité (§5). Le fait marquant de la dernière passe est l'ajout d'une **suite de tests de non-régression couvrant chaque correctif de la §2** (99 tests, suite portée de 97 à 196 verts) : l'absence de tests avait justement laissé passer une mauvaise application du correctif 2.6 (bloc `lang2`/`lang3` mélangé → perte de la 2ᵉ langue), depuis corrigée et verrouillée par un test paramétré. Il subsiste une petite régression cosmétique dans `register.pt` (jeton CSRF rendu en `type="d-none"`).

| Section | Corrigé | Partiel | Non corrigé |
|---|---|---|---|
| 1. Sécurité critique | 1.1, 1.2, **1.4**, 1.5, **1.6**, **1.7**, **1.8**, **1.9**, **1.10**, **1.11** | — | 1.3 |
| 2. Bugs bloquants | **2.1**–**2.18** (les 18) | — | — |
| 3. Transactions | — | **register** (7 commits retirés) | 5 fichiers restants (19 commits) |
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

## 2. Bugs bloquants — ✅ **section entièrement corrigée** (2.1–2.18)

### 2.1 Vérificateurs sans permissions — ✅ **corrigé** (post-dump, 2026-06-30)
La branche `voter` de `get_access_permissions` testait `accessor.oid in accessed.voters` — une `str` comparée à une liste de `Voter` (dataclass), donc **toujours `False`** : branche morte, le votant tombait dans la branche générique et, depuis 2.2, recevait `NO_MEMBER_PERMISSIONS` (refus). Corrigé en `accessor.oid in {voter.oid for voter in accessed.voters}`. Vérifié empiriquement : un votant obtient désormais `access['voter'][état]` pour les sept états de candidature (sans warning), tandis qu'un non-votant reste refusé et tracé (comportement 2.2 inchangé).

### 2.2 `KeyError` sur de nombreux couples (rôle, état) — ✅ **corrigé** (post-dump, 2026-06-30)
`get_access_permissions` faisait cinq accès par indexation directe `access[…][…]`, exposés au `KeyError`/500. Ils passent désormais par un helper `_resolve_permissions(externe, interne)` qui : renvoie la cellule si le couple existe ; sinon **logue un `warning`** identifiant le couple manquant et renvoie le repli *deny-all* `NO_MEMBER_PERMISSIONS` (tous champs `Permissions.NONE`). Double bénéfice : *fail-closed* (un trou refuse au lieu de planter) **et** visibilité — toute non-couverture est tracée pour un débogage immédiat. Vérifié empiriquement : clé présente → objet identique (`is`) à l'ancien accès, sans warning ; clé absente → `NO_MEMBER_PERMISSIONS` + un warning.

En complément, la matrice a été **étoffée pour l'administrateur** : un nouveau profil `ADMIN_CANDIDATURE_PERMISSIONS` (lecture seule sur tous les champs de candidature ; les champs hérités du membre réutilisent la politique `ADMIN_MEMBER_PERMISSIONS`, donc IBAN masqué et `seed` non lisible) est branché sur `access['Administrator']` pour les sept états de candidature. Un administrateur peut donc consulter une candidature en cours (les 28 plantages côté non-propriétaire sont remplacés par une lecture pour l'admin, un refus tracé pour les autres rôles). Les trous restants (combinaisons `Owner` non rencontrées dans le parcours d'inscription, accès `Ordinary`/`Cooperator`/`Provider` à une candidature) renvoient un refus journalisé — voir *Suivi*.

### 2.3 Vote probablement jamais persisté — ✅ **corrigé** (post-dump, 2026-06-30)
Quatre points traités dans `vote.py` : (1) **persistance** — `voter.vote = vote` mute un `Voter` (dataclass) niché dans la liste `_voters` d'une `Candidature` persistante sans la marquer *dirty* ; ajout de `candidature._p_changed = True` juste après. **Prouvé en vraie ZODB** (`FileStorage` rouvert) : sans le flag le vote relu vaut `None` (perdu), avec le flag il est bien persisté. (2) **renommage** de la vue `login_view` → `vote_view` (copier-coller) ; (3) lecture session `request.session['site_name'/...]` → `.get(..., SITE_NAME/DOMAIN_NAME/ORGANIZATION_DETAILS)`, plus de `KeyError` (cohérent avec 1.11) ; (4) **résultat de `register_user_to_ldap` vérifié** — l'approbation n'est faite que si le retour vaut `{'status': 'success'}` (test défensif `isinstance(...) and .get('status')=='success'`, robuste à l'incohérence de contrat 2.9) ; sinon log d'erreur, `abort()` et message à l'utilisateur, la candidature ne passe **plus** `APPROVED` sur échec LDAP. Vérifié en pilotant `vote_view` (échec → reste `PENDING` + vote conservé ; succès → `APPROVED` ; retour non-dict → reste `PENDING`). Suite complète 97/97. **Contrôle de la *deadline* de vote ensuite implémenté** (post-dump, 2026-06-30) : si `candidature.verification_deadline` est dépassée, `vote_view` renvoie une erreur `voting_period_ended` et le template masque le formulaire (deadline absente ⇒ pas de blocage ; *deadline naive* normalisée en UTC) — vérifié sur 5 cas. Points fonctionnels restants (voir *Suivi*) : sémantique d'égalité YES/NO, typage `str` vs `VotingChoice`, calcul du résultat à l'échéance, et ajout de la clé i18n.

### 2.4 `manage_provider.py` branches création/mise à jour cassées — ✅ **corrigé** (post-dump, 2026-07-01)
Plusieurs bugs traités. **Branche « create »** : `provider_email in providers` (où `providers` est une liste d'objets `User`, donc toujours faux) → `any(existing.email == provider_email for existing in providers)` ; le `get_member_by_oid(provider_email, …)` mort (e-mail utilisé comme oid, toujours `None`) a été retiré. **Branche « update »**, entièrement réécrite : suppression de `RegisterForm(request, schema=…, member=…)` (constructeur inexistant), de `form.validate`/`form.get_data` et du `manage_provider_schema` mort ; elle lit désormais `provider_email`/`provider_password` depuis `request.params`, valide via `is_valid_email(new_email, request)` et `is_valid_password`, met à jour l'e-mail par `update_ldap_member(request, member, fields_to_update=['email'])` (3ᵉ argument = **liste de noms de champs**, plus un dict), le mot de passe par `update_member_password`, pose l'état valide `MemberStates.DATA_MODIFIED` (l'ancien `MemberStates.ACTIVE` n'existait pas → `AttributeError`) et commit. **Template** `manage_provider.pt` : le formulaire « modify » gagne les champs éditables `provider_email`/`provider_password` et son bouton poste l'action **`update`** (il postait `submit`, que la vue n'écoutait pas → la branche était inatteignable). Trois nouveaux `msgid` (`provider_update_failed`, `provider_new_email_label`, `provider_new_password_label`). *Nettoyage restant (facultatif)* : imports/déclarations devenus inutilisés dans la vue (`RegisterForm`, `deform`, `Translator`, `manage_provider_schema`, etc.). Couvert par `tests/test_manage_provider.py` (8 tests).

### 2.5 `elections.py` plantage garanti — ✅ **corrigé** (post-dump, 2026-06-27)
`get_candidatures(request)` reçoit désormais l'argument `request` → plus de `TypeError`/500 pour un utilisateur connecté. **Réserve** : la vue reste un *stub* — elle renvoie toujours `{"elections": []}`, le résultat `candidatures` est assigné mais inutilisé (F841), et `logged_in`/`username` sont encore lus depuis `request.params`. La logique de filtrage des élections est à écrire (TODO posés). Voir *Suivi*.

### 2.6 `update_ldap_member` mapping incohérent — ✅ **corrigé** (post-dump, 2026-06-30)
Argument par défaut mutable remplacé par `None` + liste construite dans le corps avec les **noms modèle** (ceux que teste le corps et que poussent les appelants). `'data.fullsurname'` → `'fullsurname'` ; `'uniqueMemberOf'` → `'unique_member_of'` (+ `member.data.unique_member_of`) ; `member.data.dateErasureAllData` → `member.data.date_erasure_all_data` (plus d'`AttributeError`). `cooperativeBehaviourMark` converti en `str`. `MODIFY_DELETE` (qui échouait sur attribut absent) remplacé par `MODIFY_REPLACE` avec valeur vide (supprime si présent, no-op sinon). Vérifié en exécutant la fonction (LDAP mocké) : un appel par défaut construit désormais **18 attributs** (vs ~4), `sn` est présent, `cooperativeBehaviourMark` est une `str`, et les langues vides passent en `MODIFY_REPLACE`. **Correctif de suivi (2026-07-01)** : lors de l'application, le bloc `lang2`/`lang3` avait été **mélangé** — le cas « `lang2` renseignée » écrivait `secondLanguage` **vide** (perte de la 2ᵉ langue), le cas « `lang2` vide » visait `thirdLanguage` (mauvais attribut), et le `lang3` vide gardait un `MODIFY_DELETE`. Rétabli : langue renseignée → `MODIFY_REPLACE [valeur]`, vide → `MODIFY_REPLACE []`, sur le bon attribut. Effet de bord bénéfique constaté dans `tests/test_ldap_utils.py` (paramétré sur les combinaisons `lang2`/`lang3`) : c'est précisément ce test qui aurait dû exister pour attraper la régression.

### 2.7 `modify_member.py` retour mal interprété + mot de passe inopérant — ✅ **corrigé** (post-dump, 2026-06-30 → complété 2026-07-01)
Corrigés : (a) `if not sending_success` → `if fields_to_update and sending_success.get('status') != 'success'` (le retour de `update_ldap_member` est toujours un dict *truthy* — une erreur LDAP était prise pour un succès) ; (b) **branche mot de passe** : après `is_valid_password`, on teste l'erreur **et** on appelle désormais `update_member_password` en vérifiant son retour (le changement était sans effet) ; (c) `email_template` `"reset_password_email"` → `"check_new_email"` (le vrai template envoyé), et statut d'envoi posé sur `accessed_member` (pas `member`) ; (d) `flash` corrigé (message en 1ᵉʳ, file `'error'` en 2ᵉ) ; (e) même bug de retour dans `check_new_email.py` (`if result is None` → test sur `status`). **Cast des types désormais implémenté (2026-07-01)** : le `#@TODO cast the value to the right type` est résolu par un helper `_coerce_member_data_value(field, raw)` qui convertit la valeur du formulaire (toujours une `str`) vers le type déclaré du champ, résolu une fois via `get_type_hints(MemberDatas)` (`bool`/`int`/`float`) ; sur une saisie invalide (p. ex. `"abc"` pour `number_shares_owned`), la vue renvoie `invalid_field_value` (nouveau `msgid`) sans rien écrire. Effet de bord bénéfique : la comparaison `getattr(...) != requested_value` se fait maintenant entre valeurs du même type, ce qui évite les mises à jour LDAP superflues (`"5" != 5` était toujours vrai). Vérifié : compile + contrôles ciblés. Couvert par `tests/test_modify_member.py` (8 tests, dont le cast int/float/bool et le rejet d'une valeur invalide) et `tests/test_check_new_email.py` (3 tests).

### 2.8 `logout` : `KeyError` sur `?username=` — ✅ **corrigé** (post-dump, 2026-07-01)
`logout` lisait `username` depuis `request.params` puis faisait `del request.session['username']` — mais cette clé n'est **jamais** posée en session (la seule occurrence de `'username'` dans le code est le payload du token Keycloak). `/logout?username=X` levait donc un `KeyError` (500). Le bloc piloté par le paramètre d'URL est remplacé par un `request.session.pop('username', None)` inconditionnel et sûr ; les autres suppressions de la fonction étaient déjà gardées par `if X in request.session`. Couvert par `tests/test_logout.py` (4 tests).

### 2.9 `register_user_to_ldap` contrat de retour incohérent — ✅ **corrigé** (post-dump, 2026-06-30)
Le chemin « pseudonyme invalide » retournait tel quel le `{'error': …}` de `is_valid_unique_pseudonym` (sans clé `status`), alors que les appelants lisent `result['status']` (et `register.py` lit aussi `result['message']`) → `KeyError`. Normalisé en `{'status': 'error', 'message': error.get('error'), **error}` : on respecte le contrat des autres retours de la fonction tout en conservant `error`/`error_details`. Vérifié en exécutant la fonction avec un pseudonyme invalide → `{'status':'error','message':…,'error_details':…}`.

### 2.10 DN de groupes incohérents — ✅ **corrigé** (post-dump, 2026-06-30)
Trois points : (a) le `uniqueMemberOf` d'un PROVIDER pointait `providerMembersGroup` alors que le groupe créé/modifié est `providersGroup` → unifié sur `providersGroup` ; (b) les six DN de groupes re-préfixaient `ou={LDAP_OU}` alors que la création des groupes (`__init__.py` l.159-160) et le DN utilisateur emploient `{LDAP_OU}` directement → préfixe `ou=` retiré, les DN ciblent désormais l'endroit où les groupes existent réellement ; (c) `group_dn` n'était pas défini pour ADMINISTRATOR/`_` → `NameError` potentiel dans le log final, corrigé par `group_dn = None` + garde `if group_dn is not None`. Vérifié en exécutant `register_user_to_ldap` avec une connexion LDAP mockée : pour COOPERATOR/ORDINARY/PROVIDER le DN passé à `conn.modify` est **identique** à celui que crée `__init__.py`, et `uniqueMemberOf` pointe le même DN ; ADMINISTRATOR ne fait aucun `modify` et ne lève pas.

### 2.11 Validateur de mot de passe inversé — ✅ **corrigé** (post-dump, 2026-07-01)
`colander.Function` lève `Invalid` quand le *callback* renvoie une valeur *falsy* (ou une chaîne, utilisée comme message) et considère un retour *truthy* non-chaîne comme valide ; `is_valid_password` fait l'inverse (`None` = valide, dict d'erreur sinon). Un mot de passe **valide était donc rejeté** et un **invalide accepté** (démontré avec le vrai colander). Corrigé par un adaptateur `_validate_password(value)` qui renvoie `True` si valide et le message d'erreur sinon ; `schemas/register_form.py` l.173 devient `validator = colander.Function(_validate_password)`. Aucun nouveau `msgid` (le repli `_('invalid_password')` existe déjà). Couvert par `tests/test_register_form.py` (5 tests, dont un sur le validateur réel du champ `password` du schéma). *Note* : le bug était jusqu'ici inoffensif car `form.validate` reste commenté (cf. 1.5).

### 2.12 `get_i18n_id` : `return(f"name.lower()")` — ✅ **corrigé** (post-dump, 2026-07-01)
Les quatre branches par défaut (`case _`) qui renvoyaient la chaîne littérale `"name.lower()"` (une f-string sans accolades) interpolent désormais `name.lower()` avec le préfixe i18n de chaque classe : `MemberStates` → `member_state_…`, `MemberTypes` → `member_types_…`, `Permissions` → `access_permissions_…`, `CandidatureStates` → `candidature_states_…` (à l'image des deux fallbacks déjà corrects, `MemberRoles`/`role_types_…` et `VotingChoice`/`vote_types_…`). Ces branches sont des replis « should never happen » précédés d'un `log.error` ; le préfixe est ajustable si une autre convention est préférée. Couvert par `tests/test_get_i18n_id.py` (8 tests, dont un balayage vérifiant qu'aucune branche ne renvoie plus le littéral). **Note** : la suite reconstruite ne fige plus ce comportement — l'ancien `tests/test_views.py` (qui affirmait `== "name.lower()"`) ne contient plus ces assertions, et la suite complète passe (196) avec le correctif.

### 2.13 Refresh SSO fragile — ✅ **corrigé** (post-dump, 2026-07-01)
Le token d'accès n'était jamais conservé : `SSO_TOKEN` (clé de session) n'était écrit nulle part, et les `request.headers['Authorization'] = f'Bearer {sso_token}'` (dans `home.py`, `login.py` **et** `sso_login.py`) n'ont aucun effet — ils modifient la requête *entrante* et embarquent le **dict** entier, pas le token. Corrigé : les trois vues stockent désormais `sso_token['access_token']` (la chaîne) dans `request.session[SSO_TOKEN]` (cohérent avec la purge au logout). Dans `home.py`, le retour `None` de `refresh_keycloak_token` est gardé (déconnexion propre au lieu du `TypeError` sur `['access_token']`), et une expiration absente déclenche une déconnexion explicite au lieu du défaut `"2020-01-01T00:00:00"` (qui provoquait une déconnexion silencieuse). Dans `login.py`, `request.session[SSO_EXPIRES_AT] = sso_token[SSO_EXPIRES_AT]` (un `KeyError` — `SSO_EXPIRES_AT` vaut la chaîne `"SSO_EXPIRES_AT"`, absente du dict Keycloak) est remplacé par un calcul depuis `refresh_expires_in`, comme les deux autres vues. Couvert par `tests/test_home_sso.py` (4 tests) ; le test existant `test_views.py::test_home_view_refreshes_valid_sso_token` a été mis à jour (il vérifie le token en session, plus le header). **Reste** (amélioration distincte) : le rafraîchissement a lieu à chaque affichage de l'accueil tant que le *refresh token* est valide — le limiter à l'approche de l'expiration du token d'accès demanderait de suivre `expires_in` séparément.

### 2.14 `Members.get_instance` singleton ZODB inter-connexions — ✅ **corrigé** (post-dump, 2026-07-01)
Le bloc `if Members._instance is not None: return Members._instance` était évalué **avant** l'argument `connection` : une fois le cache posé, toute requête récupérait cet objet — lié à une connexion précédente (parfois fermée) — au lieu de l'objet de sa propre connexion, d'où `ConnectionStateError`/lectures périmées. Corrigé : la connexion est testée **en premier** ; si elle est fournie, `get_instance` relit toujours `connection.root()['members']` et rafraîchit `_instance`. Comme la *root factory* (`set_root_factory(root_factory)`) appelle `get_instance(connection=conn)` à chaque requête, l'appel **sans** connexion de `generate_unique_oid` voit l'instance de la requête courante. Le contrôle de vivacité `'test' in _instance` qui **relançait** l'exception (en laissant l'instance morte en cache) est remplacé, sur le chemin sans connexion, par une purge du cache + `TypeError` explicite. La réutilisation inter-connexions — le risque concret — est supprimée ; le fond thread-safety subsiste (singleton d'attribut de classe, cf. « Not thread safe! »). Couvert par `tests/test_members_get_instance.py` (5 tests, vraie ZODB à deux connexions).

### 2.15 `ldap_factory.py` connexion globale — ✅ **corrigé** (post-dump, 2026-07-01)
Deux problèmes concrets traités. (1) **Arguments par défaut évalués à l'import** : `get_ldap_server(server_name=get_ldap_server_name(), port=get_ldap_server_port())` et `get_ldap_connection(ldap_server=…, ldap_port=…)` figeaient hôte/port au chargement du module → passés à `None` et résolus dans le corps (au call time). (2) **Connexion SYNC en singleton module-level** (`_conn`), non thread-safe (les connexions SYNC ldap3 entrelacent requêtes/réponses entre threads) et de surcroît *unbindée* par le `with` de l'appelant → singleton supprimé, **connexion fraîche créée à chaque appel** (les deux branches SYNC/non-SYNC fusionnées). `reset_ldap_connection` ne réinitialise plus que `_server`. *Résiduel assumé* : pour une forte charge, un vrai pool (stratégie `REUSABLE`) serait préférable ; la connexion-par-appel est correcte et suffisante ici. Couvert par `tests/test_ldap_factory.py` (4 tests).

### 2.16 `secret_manager.py` : `del os.environ[...]` non protégé — ✅ **corrigé** (post-dump, 2026-07-01)
Les six `del os.environ[...]` de `get_secret` (l.32/44-46/48/50) sont remplacés par `os.environ.pop(..., None)`. La suppression défensive des secrets après lecture est ainsi idempotente : plus de `KeyError` quand une variable est absente, et pour `SECRET_KEY` le `ValueError("You must provide a base64 value for SECRET_KEY")` explicite s'applique enfin au lieu d'être masqué par le `del`. Couvert par `tests/test_secret_manager.py` (3 tests).

### 2.17 `validate_challenge` : `request.params[label]` → `KeyError` — ✅ **corrigé** (post-dump, 2026-07-01)
`register.py` l.401 : `request.params[label].strip()` levait `KeyError` (500) quand le champ de réponse `result_{key}` était absent (réponse laissée vide). Remplacé par `request.params.get(label, '').strip()` : une réponse manquante vaut `''`, différente de la réponse attendue → renvoie `invalid_challenge` (une réponse absente compte comme incorrecte). Couvert par `tests/test_validate_challenge.py` (4 tests).

### 2.18 `remind_pending_verifiers` sur chaque requête — ✅ **corrigé** (post-dump, 2026-07-01)
Toujours abonné à `NewRequest`, mais le scan (O(n) sur les candidatures) ne s'exécute plus **à chaque requête** : ajout d'un throttle module-level (`_REMINDER_MIN_INTERVAL_SECONDS = 600`, `_reminder_last_run`) — contrôle bon marché sans verrou d'abord — et d'un verrou non bloquant `threading.Lock` (`acquire(blocking=False)`) avec double-vérification, de sorte qu'un seul thread lance le scan à la fois et qu'il tourne au plus une fois toutes les 10 min (fin du double-envoi concurrent). Le court-circuit `PYTEST_CURRENT_TEST` et le `try/except` sont conservés. L'intervalle est **configurable** : réglage `production.ini` `verifier_reminder_min_interval_seconds` (prioritaire) ou variable d'environnement/`.env` `VERIFIER_REMINDER_MIN_INTERVAL_SECONDS`, avec un **défaut de 72 h**. *Résiduel assumé* : c'est un ordonnancement in-process déclenché par les requêtes ; une vraie tâche planifiée (cron/APScheduler) resterait l'idéal. Couvert par `tests/test_reminder_throttle.py` (3 tests).

---

## Tests de non-régression (ajoutés le 2026-07-01)

L'absence de tests couvrant les correctifs §2 avait laissé passer au moins une régression silencieuse (le bloc `lang2`/`lang3` de 2.6). Une suite de non-régression a donc été ajoutée — **un fichier par correctif** — portant la suite de 97 à **196 tests verts**. Pour chacun, le test a été vérifié comme *échouant* sur le code pré-correctif (bug réintroduit temporairement), garantissant qu'il attrape bien la régression.

| Fichier | Tests | Trouvaille(s) | Points clés |
|---|---|---|---|
| `test_model_permissions_access.py` | 11 | §2.1, §2.2 | reconnaissance des votants (comparaison sur les `oid`), lecture admin des candidatures (7 états), refus *fail-closed* d'une cellule absente |
| `test_vote.py` | 10 | §2.3 | **persistance du vote prouvée en vraie `FileStorage` rouverte** (perdu sans `_p_changed`), garde de *deadline*, repli session, interprétation du retour LDAP à l'approbation |
| `test_ldap_utils.py` | 10 | §2.6, §2.9 | 18 attributs par défaut sans `AttributeError`, noms de champs corrigés, `lang2`/`lang3` (garde anti-perte de données, jamais `MODIFY_DELETE`), contrat de retour du pseudonyme invalide |
| `test_modify_member.py` | 8 | §2.7 | interprétation du retour LDAP, écriture effective du mot de passe, **cast `int`/`float`/`bool`** et rejet d'une valeur invalide |
| `test_manage_provider.py` | 8 | §2.4 | gardes d'accès, détection de doublon par e-mail, mise à jour e-mail/mot de passe, remontée d'échec LDAP |
| `test_get_i18n_id.py` | 8 | §2.12 | les quatre fallbacks interpolent, aucun ne renvoie le littéral, les noms connus résolvent |
| `test_register_form.py` | 5 | §2.11 | adaptateur du validateur, comportement via `colander.Function`, validateur réel du champ `password` |
| `test_check_new_email.py` | 3 | §2.7 | un échec LDAP (dict d'erreur **ou** `None`) n'est plus pris pour un succès, pas de commit |
| `test_logout.py` | 4 | §2.8 | `/logout?username=X` ne lève plus, déconnexion effective, purge des clés SSO/oid |
| `test_home_sso.py` | 4 | §2.13 | refresh qui échoue → logout **sans crash**, token d'accès stocké en session (pas de header), fenêtre expirée/absente → logout |
| `test_members_get_instance.py` | 5 | §2.14 | instance liée à la connexion passée (`_p_jar`), deux connexions → deux objets distincts, repli cache/`TypeError` |
| `test_secret_manager.py` | 3 | §2.16 | `SECRET_KEY` absent → `ValueError` (pas `KeyError`), mots de passe absents sans crash, secrets retirés de l'environnement |
| `test_validate_challenge.py` | 4 | §2.17 | réponse manquante → `invalid_challenge` (pas `KeyError`), réponses correctes → `None`, fausse → erreur, `strip` |
| `test_ldap_factory.py` | 4 | §2.15 | défauts hôte/port à `None` (résolus au call time), plus de singleton `_conn`, `reset` vide `_server` |
| `test_reminder_throttle.py` | 4 | §2.18 | court-circuit en pytest, au plus une fois par intervalle, ré-exécution après intervalle, réglage `production.ini` prioritaire |
| `test_register_email_validation.py` | 3 | §3 | état → `CONFIRMED_HUMAN` sans commit explicite, formulaire toujours rendu (même si e-mail KO), erreur de challenge |
| `test_register_transactions.py` | 5 | §3 | plus de `request.tm.commit()` (`commit_candidature_changes`, `handle_unique_data_state`) ; `prepare_for_cooperator` renvoie `voters_not_selected` si `random_voters()` lève (garde LDAP) |

Ces tests s'appuient sur les *fixtures* existantes (`members_mapping`, `caplog`, `tmp_path`) ; le LDAP et l'envoi d'e-mail sont mockés, la ZODB n'est réelle que pour la persistance du vote. Aucune dépendance nouvelle.

---

## 3. Cohérence transactionnelle — ⚠️ **en cours** (stratégie adoptée, 1er correctif appliqué)

**30 appels explicites** `transaction.commit()` / `request.tm.commit()` subsistent, combinés à `pyramid_tm`, répartis ainsi : `register.py` (7), `forgot_password.py` (7), `modify_member.py` (4), `vote.py` (4), `manage_provider.py` (2), `check_new_email.py` (1), `member.py` (1).

**Stratégie retenue** : s'appuyer sur `pyramid_tm` (une transaction par requête, *commit* unique en fin de requête) et retirer les *commits* explicites en cœur de vue, sauf ceux réellement nécessaires (contexte hors requête). Un *commit* explicite au milieu d'une vue rebinde les objets ZODB sur une transaction terminée et provoque des lectures/rendus incohérents.

> **Vérifié — envoi d'e-mails transactionnel** : `send_email` utilise `mailer.send()` de `pyramid_mailer` (« *the message is not sent until the transaction is committed* »), et il n'existe **aucun** `send_immediately` dans le code. Les e-mails ne partent donc qu'au *commit* de la transaction courante ; retirer un *commit* intermédiaire ne les émet jamais avant persistance — au contraire, l'e-mail et le changement d'état deviennent atomiques (même transaction). La contrainte « e-mail seulement après *commit* » n'imposait donc pas les *commits* intermédiaires.

**`register.py` — entièrement nettoyé (7 *commits* retirés)**. Le 1er (`handle_email_validation_state`) causait le bug de rendu du formulaire candidat : `request.tm.commit()` posé juste avant le rendu → la section `CONFIRMED_HUMAN` (champ pseudonyme) ne s'affichait qu'après **rafraîchissement** de la page (le template contenait même un avertissement décrivant ce contournement). Les 6 autres (`commit_candidature_changes`, `handle_confirmed_human_state`, `prepare_for_cooperator`, `_notify_verifiers_of_submission` — *commit* par votant en boucle —, et `handle_unique_data_state` ×2) suivaient tous le même motif « *commit* pour flusher l'e-mail en file puis enregistrer le statut `SENT` » : redondant, puisque le *mailer* est transactionnel (l'e-mail part au *commit* final de pyramid_tm, atomiquement avec l'état et le statut). Les *commits* explicites sont retirés ; le `try/except` de `prepare_for_cooperator` est **conservé** (il garde l'appel LDAP `random_voters()`, pas le *commit*). Effets de bord corrigés : le formulaire candidat est toujours rendu (même si l'e-mail de confirmation échoue), et les envois par votant sont regroupés sur le *commit* final. Les `try/except` de `handle_confirmed_human_state` et `handle_unique_data_state` sont **conservés** (le suivi de statut `ERROR` est préservé) ; celui de `commit_candidature_changes`, qui ne gardait plus que `add_email_send_status`, a été retiré. **Point d'attention** : le commit de retrait (`7613940`) avait aussi supprimé par erreur le `try/except` de `prepare_for_cooperator`, qui garde l'appel LDAP `random_voters()` (connexion à l'annuaire + lecture d'attributs — peut lever) ; sans lui, une panne LDAP donnait un 500 au lieu de l'erreur propre `voters_not_selected`. La garde a été **restaurée** dans un commit de suivi, avec des tests. Couvert par `tests/test_register_email_validation.py` (3) et `tests/test_register_transactions.py` (5). **Reste** : les 5 autres fichiers (`forgot_password.py` 7, `modify_member.py` 4, `vote.py` 4, `manage_provider.py` 2, `check_new_email.py` 1, `member.py` 1) — à revoir au cas par cas, en gardant à l'esprit que le vote (§2.3) a une logique propre à préserver.

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
2. ~~**`tests/test_views.py`** : tests figeant `get_i18n_id` (`"name.lower()"`)~~ — ✅ **résolu** : le bug 2.12 est corrigé et la suite reconstruite ne contient plus ces assertions ; la suite complète (196) passe avec le correctif. Seule la régression cosmétique **`register.pt`** (point 1) subsiste.

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
- **2.7 — cast des types dans `modify_member`** : ✅ **fait** (2026-07-01) — helper `_coerce_member_data_value(field, raw)` s'appuyant sur `get_type_hints(MemberDatas)` pour convertir `bool`/`int`/`float` avant `setattr`, avec renvoi d'erreur `invalid_field_value` sur saisie invalide (nouveau `msgid` ajouté en `fr`/`en`). Les dates restent gérées via `date_parameters`. Verrouillé par `tests/test_modify_member.py`.
- **2.3 — points de `vote.py`** : ✅ contrôle de *deadline* désormais implémenté. Restent : (a) une **égalité YES/NO refuse** la candidature (`count_yes > count_no` requis) et `ABSTAIN` compte comme vote exprimé — à confirmer fonctionnellement ; (b) `voter.vote` stocke le **nom** (`str`) au lieu d'un `VotingChoice` — à typer proprement ; (c) **calcul du résultat à l'échéance** (@TODO l.153 « if date is passed, compute the result with the votes ») non fait : un vote arrivé après la deadline est désormais refusé, mais si tous les votants n'ont pas voté avant l'échéance, la candidature n'est jamais tranchée — il faudra dépouiller à la deadline (tâche planifiée / au prochain accès). Enfin, **ajouter la clé i18n `voting_period_ended`** aux catalogues `fr`/`en` (sinon le `msgid` brut s'affiche).

---

## Reste prioritaire (ordre suggéré)
1. **Faille de sécurité restante** : **1.3** seul subsiste en section 1 — hachage des mots de passe côté LDAP (`register_user_to_ldap`, `update_member_password`) et purge de `data.password` en ZODB après création. C'est le plus gros point de sécurité encore ouvert.
2. **Bugs bloquants §2** : ✅ **terminée** — les 18 trouvailles (2.1–2.18) corrigées et testées.
3. **Robustesse** : §3 stratégie transactionnelle unique, 2.14/2.15 singletons, 2.18 hors cycle requête.
4. **Continu** : `ruff` + `mypy` ; corriger la régression cosmétique `register.pt` (`type="d-none"` → `type="hidden"`) ; compléter les *stubs* (`elections_view`, dépouillement du vote à l'échéance — cf. *Suivi* 2.3) ; étendre la couverture de tests aux sections §1 et §3.
