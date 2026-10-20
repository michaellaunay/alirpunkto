# La situation financière d'un Coopérateur

Couvre les issues #75 (suivi des faits financiers), #148 (transitions
entre groupes dynamiques), #267 (mise à jour à l'encaissement) et #269
(propagation au SSO).

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
commercial appelle `tools/update_cooperator.py`, qui ouvre une session
**d'administrateur** sur AlirPunkto et soumet les nouveaux faits au point
d'entrée dédié `POST /update_contribution` :

| Paramètre | Rôle |
|---|---|
| `oid` | le numéro du Coopérateur (obligatoire) |
| `number_shares_owned` | nouveau nombre de parts (entier ≥ 0) |
| `date_end_validity_yearly_contribution` | nouvelle échéance, `AAAA-MM-JJ` |
| `csrf_token` | le jeton de la session (garde CSRF globale) |

Au moins un des deux faits est requis ; **aucun autre champ n'est
accepté** — la fiche d'un autre membre reste en lecture seule pour tout
le monde, administrateurs compris (#149). La réponse est du JSON :
`status`, `updated_fields`, les deux faits après écriture et `groups`,
la liste des groupes dynamiques du membre **après** la transition.

L'effet est **immédiat** : l'écriture dans l'annuaire déclenche le
synchroniseur de groupes (#148) puis la propagation vers Keycloak
(#269), si bien que le Coopérateur retrouve ses droits sur l'ensemble des
applications sans attendre sa prochaine connexion ni le scan quotidien.

Refus (JSON `{"status": "error", "error": …}`) : `405` hors `POST`,
`401` sans session, `403` si la session n'est pas celle d'un
administrateur, `400` paramètre manquant ou invalide (`fields` nomme les
fautifs), `404` membre inconnu, `409` si le membre n'est pas un
Coopérateur, `502` si l'annuaire refuse l'écriture.

## Le script

```
python tools/update_cooperator.py --env shop.env --oid <uuid> \
    --number-shares 1 --validity-date 2027-06-30 \
    --base_url https://access.example.coop
```

Le script se connecte, lit le jeton CSRF sur la page de l'annuaire des
membres, poste les faits et **échoue bruyamment** (`RuntimeError`) sur
tout refus — un encaissement non répercuté ne doit plus passer
inaperçu.

## Le scan quotidien (#148, #269)

Le reste du temps, c'est la maintenance quotidienne qui transforme le
calendrier en transitions (cotisation échue) et prévient le SSO ; voir
[09_taches_periodiques](../architecture/09_taches_periodiques.md).
