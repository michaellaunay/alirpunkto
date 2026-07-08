# Glossary

> English equivalents of the French business terms used in the code, the
> templates and the documentation. The French term is given when it
> appears as such in the interface or the code.

- **Member** (*membre*): a registered person; a `Member` object in the
  ZODB, an `alirpunktoPerson` entry in LDAP. Types: administrator,
  ordinary member, cooperator, provider (`MemberTypes`).
- **Cooperator** (*coopérateur*): a member holding at least one share and
  up to date with their contribution; belongs to `cooperatorsGroup`.
- **Ordinary member**: a community member without shares;
  `ordinaryMembersGroup`.
- **Provider** (*prestataire*): a service provider of the cooperative
  (`providersGroup`), managed through the `manage_provider` view.
- **Candidature**: a membership application; a `Candidature` object
  (inheriting from `Member`) with its state machine
  (`CandidatureStates`).
- **Challenge** (*défi*): the arithmetic question sent by e-mail to verify
  that an applicant is human.
- **Verifier** (*vérificateur*, `Voter` in the code): a member drawn at
  random to review a candidature and vote (`VotingChoice`: yes, no,
  abstain).
- **oid**: a member's unique identifier (UUID); it is also the LDAP `uid`
  and the `employeeNumber`.
- **Pseudonym**: the member's public name (LDAP `cn`); the civil identity
  stays confidential.
- **Cooperative behaviour mark**: an engagement score
  (`cooperativeBehaviourMark`, with its update date).
- **Share** (*part sociale*): a stake in the capital
  (`numberSharesOwned`).
- **Yearly contribution**: the membership fee; its validity is bounded by
  `dateEndValidityYearlyContribution`.
- **Board**: `boardMembersGroup` (role `BOARD`).
- **Mediation and Arbitration Council**:
  `mediationArbitrationCouncilGroup`.
- **Placeholder member**: the dummy entry
  `uid=00000000-…,cn=admin,<base>` present in every LDAP group to satisfy
  `groupOfUniqueNames`.
- **SSO**: single sign-on through Keycloak, backed by the same directory.
- **{SSHA}**: the salted hashing scheme for passwords in LDAP.
