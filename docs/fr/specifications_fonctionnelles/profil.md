# Le profil du membre

Couvre les issues #55 (matrice des champs), #123 (cadre de la vue),
#149 (fiche administrateur), #201 et #249 (visibilité), #263 et #270
(contenu de la fiche publique).

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
présentation, avatar, numéro, courriel (#249), rôle, CBM et sa date, date
et motif du départ. Rien d'autre n'est transmis (ni IBAN, ni identité
civile), la consultation ne change pas l'état du membre, et aucune
soumission sur cette page ne peut aboutir à une écriture.

Les **faits financiers** d'un Coopérateur (parts détenues, échéance de la
cotisation annuelle — #75) ne se modifient pas par cette fiche : ils ont
leur propre chemin d'écriture administratif, décrit dans
[situation_financiere](situation_financiere.md) (#267).

## Ce que les autres membres voient (issues #249, #263, #270)

Tout membre connecté parcourt l'annuaire des membres et peut ouvrir la
**fiche publique** d'un autre membre — jamais son formulaire : pseudonyme,
**texte de présentation** et **avatar** (#270, pour se faire une idée de
la personne), rôle dans la Coopérative (#263), CBM et sa date de mise à
jour. Ni courriel, ni numéro, ni IBAN, ni identité civile : ces éléments
restent réservés à la fiche administrateur. Les interactions entre
membres ont lieu sur l'espace de travail partagé.
