# Glossaire

> Termes métier français en usage dans le code, les gabarits et la
> documentation.

- **Membre** : personne inscrite ; objet `Member` en ZODB, entrée
  `alirpunktoPerson` dans LDAP. Types : administrateur, membre ordinaire,
  coopérateur, prestataire (`MemberTypes`).
- **Coopérateur** : membre ayant souscrit au moins une part sociale et à
  jour de sa contribution ; appartient à `cooperatorsGroup`.
- **Membre ordinaire** : membre de la communauté sans part sociale ;
  `ordinaryMembersGroup`.
- **Prestataire** : fournisseur de services de la coopérative
  (`providersGroup`), géré via la vue `manage_provider`.
- **Candidature** : demande d'adhésion ; objet `Candidature` (héritant de
  `Member`) avec sa machine à états (`CandidatureStates`).
- **Défi** (*challenge*) : question arithmétique envoyée par courriel pour
  vérifier qu'un candidat est humain.
- **Vérificateur** (*voter*) : membre tiré au sort pour instruire une
  candidature et voter (`VotingChoice` : oui, non, abstention).
- **oid** : identifiant unique d'un membre (UUID) ; il est aussi le `uid`
  LDAP et l'`employeeNumber`.
- **Pseudonyme** : nom public du membre (`cn` LDAP) ; l'identité civile
  reste confidentielle.
- **Marque de comportement coopératif** : note d'engagement
  (`cooperativeBehaviourMark`, avec sa date de mise à jour).
- **Part sociale** : participation au capital (`numberSharesOwned`).
- **Contribution annuelle** : cotisation ; sa validité est bornée par
  `dateEndValidityYearlyContribution`.
- **Conseil d'administration** : `boardMembersGroup` (rôle `BOARD`).
- **Conseil de Médiation et d'Arbitrage** :
  `mediationArbitrationCouncilGroup`.
- **Groupe de remplissage** : membre factice
  `uid=00000000-…,cn=admin,<base>` présent dans chaque groupe LDAP pour
  satisfaire `groupOfUniqueNames`.
- **SSO** : authentification unique via Keycloak, adossée au même annuaire.
- **{SSHA}** : schéma de hachage salé des mots de passe dans LDAP.
