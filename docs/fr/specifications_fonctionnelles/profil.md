# Le profil du membre

Couvre les issues #55 (matrice des champs), #123 (cadre de la vue),
#149 (fiche administrateur) et #201 (visibilité).

## Sa propre page

Tout membre connecté qui ouvre « Modifier mes données » atterrit
directement sur **son** profil : le titre « Ton profil », l'introduction,
puis — hors formulaire — **ses groupes d'appartenance** (libellés
traduits) et, pour un Coopérateur ou assimilé, **son rôle** dans la
Coopérative. Le formulaire suit la matrice ci-dessous et se termine par
les boutons **Soumettre** et **Annuler** ; annuler recharge le profil
vierge de toute saisie (aucun accès à l'annuaire avant la redirection).

## La matrice des champs (issue #55)

| Élément | Tout membre | Coopérateur ou assimilé |
|---|---|---|
| Texte de présentation, avatar, courriel, langues | voir + modifier | voir + modifier |
| IBAN | — | voir + modifier |
| Pseudonyme, numéro d'utilisateur·rice, groupes | voir | voir |
| Identité (prénoms, noms, naissance), nationalité | — | voir |
| CBM et sa date de mise à jour, parts, échéance de cotisation, rôle | — | voir |
| Date d'effacement (#54) | jamais | jamais |

« Coopérateur ou assimilé » désigne les membres des six groupes
coopérateurs (candidats aux compléments, sanctionnés inclus). La
modification du courriel passe par la confirmation par lien
([changement d'adresse](../architecture/07_messagerie.md)) ; celle du
mot de passe par les champs dédiés. Un membre dont la démission est en
attente accède normalement à son profil — c'est là que vit « Annuler ma
demande de désactivation ».

## La consultation par un administrateur (issue #149)

L'administrateur qui ouvre le profil d'un autre membre obtient une
**fiche en lecture seule** — jamais le formulaire : pseudonyme, texte de
présentation, avatar, numéro, rôle, CBM et sa date, date et motif du
départ. Rien d'autre n'est transmis (ni courriel, ni IBAN, ni identité
civile), la consultation ne change pas l'état du membre, et aucune
soumission ne peut aboutir à une écriture.

## Ce que les autres ne voient pas (issue #201)

Un membre non administrateur n'a **aucun accès** au profil d'un autre :
ni liste des membres, ni consultation — les interactions entre membres
ont lieu sur l'espace de travail partagé.
