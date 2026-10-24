# La situation financière d'un Coopérateur

Couvre les issues #75 (suivi des faits financiers), #148 (transitions
entre groupes dynamiques), #267 (mise à jour à l'encaissement) et #269
(propagation au SSO), ainsi que l'audit externe du 24 octobre 2026
(train 0117).

## Les deux faits

L'annuaire porte, pour chaque Coopérateur, deux attributs que le ticket
#75 confie au **site commercial en ligne** :

- `numberSharesOwned` — le nombre de parts sociales détenues (entier
  positif ou nul, `0` à l'inscription) ;
- `dateEndValidityYearlyContribution` — la date de fin de validité de la
  cotisation annuelle (une date passée à l'inscription).

Ces deux faits, avec la sanction et le rôle, déterminent le groupe
dynamique du membre (#148) : parts et cotisation valide font un
**Coopérateur de plein droit** (`cooperatorsGroup`) ; une cotisation
échue le ramène parmi les candidats attendant leur cotisation.

## La mise à jour à l'encaissement (#267)

Dès qu'un Coopérateur paie sa cotisation (ou souscrit des parts), le site
commercial appelle le script client (`tools/update_cooperator.py`, ou
son portage PHP tenu par la boutique), qui ouvre une session
**d'administrateur** sur AlirPunkto et soumet les nouveaux faits au point
d'entrée dédié `POST /update_contribution` :

| Paramètre | Rôle |
|---|---|
| `oid` | le numéro du Coopérateur (obligatoire) |
| `number_shares_owned` | nouveau nombre de parts (entier ≥ 0 — `0` est une valeur) |
| `date_end_validity_yearly_contribution` | nouvelle échéance, `AAAA-MM-JJ` |
| `csrf_token` | le jeton de la session (garde CSRF globale) |

Au moins un des deux faits est requis ; **aucun autre champ n'est
accepté** — la fiche d'un autre membre reste en lecture seule pour tout
le monde, administrateurs compris (#149).

### Les trois résultats d'un encaissement

Un encaissement n'est pas « deux attributs écrits » : c'est un
Coopérateur qui retrouve ses droits. La réponse rend donc compte de trois
étapes, pas d'une :

| Champ | Valeurs | Sens |
|---|---|---|
| `financial_update` | `success`, `unchanged` | les faits dans l'annuaire (`unchanged` : ils y étaient déjà) |
| `groups_sync` | `success`, `error` | les groupes dynamiques convergés (#148) |
| `keycloak_sync` | `success`, `error` | le changement parvenu à Keycloak (#269) |
| `groups` | liste, ou `null` | les groupes dynamiques du membre **après** la transition ; `null` quand l'annuaire n'a pas pu être relu (jamais `[]` pour cela) |

Le `status` global vaut `success` seulement si les trois étapes le sont,
et `partial` — toujours en HTTP 200, car les faits **sont** enregistrés —
quand les groupes ou Keycloak sont en retard ou que les groupes ne
peuvent être relus. La réponse porte aussi `oid`, `updated_fields` et les
deux faits après écriture, pour que l'appelant vérifie que le portail a
appliqué **ses** valeurs à **son** membre.

Une réponse `partial` est **rejouable** : le même appel n'écrit rien
(`financial_update: unchanged`) mais relance le synchroniseur de groupes
et la propagation Keycloak, si bien que la reprise peut réparer ce qui a
traîné. Le scan quotidien (#148, #269) reste le dernier filet.

Refus (JSON `{"status": "error", "error": …}`) : `405` hors `POST`,
`401` sans session, `403` si la session n'est pas celle d'un
administrateur, `400` paramètre manquant ou invalide (`fields` nomme les
fautifs) ou CSRF refusé (jeton, ou `Origin`/`Referer` en HTTPS), `404`
membre inconnu, `409` si le membre n'est pas un Coopérateur, `502` si
l'annuaire refuse l'écriture.

## Le script

```
python tools/update_cooperator.py --env shop.env --oid <uuid> \
    --number-shares 1 --validity-date 2027-06-30 \
    --base_url https://access.example.coop
```

Ce que le fil exige, et ce que fait le script :

1. `GET /login` ouvre la session et porte son `csrf_token` ;
2. `POST /login` avec les identifiants, ce jeton et un en-tête `Origin`
   (et `Referer`) nommant le portail — la garde CSRF globale répond 400 à
   un POST nu, avant même de regarder les identifiants ;
3. `GET /modify_member` : une session connectée rend l'annuaire des
   membres avec son `csrf_token`, une session anonyme est renvoyée à
   l'accueil sans lui — c'est la vérification de connexion, et le jeton
   de l'étape 4 ;
4. `POST /update_contribution` avec les faits, le jeton et les mêmes
   en-têtes ; chaque appel a un délai de connexion et de lecture.

**Le code de sortie 0 signifie, et signifie seulement** : les faits sont
dans l'annuaire avec les valeurs demandées (OID et valeurs vérifiés dans
la réponse), les groupes dynamiques sont convergés et le changement a
atteint Keycloak — le client exige que `financial_update`, `groups_sync`
et `keycloak_sync` le disent et que `groups` soit une liste ; un simple
`success` n'est pas cru. Côté serveur, ces indicateurs sont honnêtes
depuis le train 0119 : une écriture d'appartenance refusée fait répondre
le synchroniseur de groupes en échec, et un `SynchronizationResult`
Keycloak avec `failed > 0` n'est pas une propagation. Tout refus, écart ou réponse `partial` sort en 1 avec
le motif du portail — un encaissement qui n'a pas restauré les droits ne
doit jamais passer inaperçu. Un appel qui ne demande aucun changement
est aussi une erreur, jamais une sortie 0 silencieuse ; `--base_url`
doit être l'origine du portail (`schéma://hôte`).

Les tests unitaires du script sont adossés à
`tests/test_update_contribution_wire.py`, qui fait passer ses fonctions
`login` et `modify_member` par la vraie pile Pyramid (schéma HTTPS,
cookie sécurisé, garde CSRF) en ne simulant que les bords LDAP et
Keycloak.

## Le scan quotidien (#148, #269)

Le reste du temps, c'est la maintenance quotidienne qui transforme le
calendrier en transitions (cotisation échue) et prévient le SSO ; voir
[09_taches_periodiques](../architecture/09_taches_periodiques.md).

## Limite connue — encaissements désordonnés

Le point d'entrée reçoit une valeur **absolue**, pas un événement de
paiement : deux notifications du même Coopérateur traitées dans le
désordre laissent l'ancien total dans l'annuaire. Un identifiant
d'opération commerciale avec une séquence croissante, permettant au
portail de refuser un état périmé, est la réponse à moyen terme (audit
externe du 24 octobre 2026, §4) ; elle n'entre pas dans le train 0117.
