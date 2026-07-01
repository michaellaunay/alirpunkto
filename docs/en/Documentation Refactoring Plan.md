# AlirPunkto Architecture Documentation Refactoring Plan

> Status: documentation action plan  
> Date: 2026-07-01  
> Language: English  
> Scope: reorganization and progressive rewrite of the AlirPunkto design, architecture and functional documentation.

## 1. Current situation

Most of the current design documents under `docs/fr/` and `docs/en/` originate from the initial project specifications and early design notes.

They remain useful for understanding the origins of AlirPunkto, but they no longer accurately describe the current code architecture.

The application has evolved into a structured system including:

- a Pyramid application served by Waitress;
- TAL/METAL templates rendered with Chameleon;
- application persistence in ZODB;
- OpenLDAP as the account and group directory;
- a custom AlirPunkto LDAP schema;
- application email through Pyramid Mailer and Postfix;
- Pyramid session-based authentication;
- optional Keycloak/SSO integration;
- global CSRF protection;
- secure session cookies;
- a Docker deployment stack;
- a local/offline Docker test stack;
- a pytest regression test suite;
- review tooling, including `tools/export_sources_for_review.sh`.

The old scenarios should therefore be preserved, but clearly separated from the current documentation.

## 2. Goals

The documentation refactoring has six goals.

1. **Separate historical material from current documentation**  
   Initial project specification documents must be archived explicitly, not deleted.

2. **Document the real architecture**  
   Documentation must describe the current code, real services, existing modules and implemented flows.

3. **Create maintainable documentation**  
   Documents should be short, topic-based and cross-linked, instead of long monolithic scenarios.

4. **Help new contributors**  
   A developer should quickly understand the components, main flows, domain model, tests and known risks.

5. **Prepare future changes**  
   Documentation must clearly distinguish current architecture, known limitations and target evolutions, especially the planned ACL and permissions refactoring.

6. **Preserve traceability**  
   Historical documents must remain accessible with a clear warning that they are no longer normative.

## 3. Proposed name for the historical archive

The French name `spec_initiales` is understandable but too ambiguous.

Recommended names:

```text
docs/fr/specifications_historiques/
docs/en/historical_specifications/
```

This naming is explicit, neutral and clear.

It is better than:

- `spec_initiales`, which is too short and not explicit enough;
- `legacy_specs`, which is technical but less clear for French readers;
- `old_docs`, which is too vague;
- `archives`, which is too broad;
- `initial_project_specifications`, which is precise but too restrictive because some documents are design notes rather than specifications.

## 4. New documentation source-of-truth rule

From this refactoring onward, documentation should follow this hierarchy:

1. **Code and tests are the technical source of truth.**
2. **Architecture documentation describes current behaviour.**
3. **Current functional specifications describe accepted business flows.**
4. **Historical specifications describe the initial intent and are not normative.**
5. **Design journals explain decisions, changes of direction and documentation migrations.**

When a historical document contradicts current code or architecture documentation, the current code and architecture documentation take precedence.

## 5. Proposed documentation tree

```text
docs/
├── README.md
│
├── fr/
│   ├── Journal de conception.md
│   ├── Plan de refonte documentaire.md
│   ├── architecture/
│   ├── specifications_fonctionnelles/
│   └── specifications_historiques/
│       ├── README.md
│       └── ...
│
└── en/
    ├── DesignJournal.md
    ├── Documentation Refactoring Plan.md
    ├── architecture/
    ├── functional_specifications/
    └── historical_specifications/
        ├── README.md
        └── ...
```

## 6. Warning to add to historical specifications

Each historical folder should contain a `README.md` with a clear warning.

Suggested text for `docs/en/historical_specifications/README.md`:

```markdown
# Historical Specifications

This directory contains the scenarios and design documents written at the beginning of the AlirPunkto project.

They are preserved for historical context, traceability and understanding of the original project intent.

These documents no longer necessarily describe the current application and must not be used as normative documentation.

Current documentation is located in:

- `docs/en/architecture/`
- `docs/en/functional_specifications/`

When a discrepancy exists, the current code, tests and architecture documentation take precedence.
```

## 7. Documents to create first

The refactoring should be progressive. The recommended order is as follows.

### Phase 1 — Documentation framework

- `docs/fr/Plan de refonte documentaire.md`
- `docs/en/Documentation Refactoring Plan.md`
- `docs/fr/specifications_historiques/README.md`
- `docs/en/historical_specifications/README.md`
- update `docs/fr/Journal de conception.md`
- update `docs/en/DesignJournal.md`

### Phase 2 — Current architecture

Create architecture documents describing the current code:

1. `00_overview.md`
2. `01_runtime_architecture.md`
3. `02_domain_model.md`
4. `03_zodb_persistence.md`
5. `04_ldap.md`
6. `05_authentication.md`
7. `06_authorization_permissions.md`
8. `07_email.md`
9. `08_third_party_applications.md`
10. `09_periodic_tasks.md`
11. `10_internationalization.md`
12. `11_security.md`
13. `12_testing.md`
14. `13_docker_deployment.md`

### Phase 3 — Current functional specifications

Rewrite the functional scenarios according to the real or near-target state of the project:

- candidature;
- login;
- password reset;
- member profile consultation and update;
- member management;
- candidature management;
- third-party application configuration;
- resignation or account deactivation, if this flow is still retained.

### Phase 4 — Architecture decisions

Create an architecture decisions document.

First decisions to document:

- why Pyramid is used;
- why ZODB is used;
- why OpenLDAP is the identity repository;
- why a custom LDAP schema exists;
- why Chameleon/TAL/METAL is used;
- why Postfix is used;
- why Docker is used;
- testing strategy;
- current permissions model;
- future target for class-based ACLs.

### Phase 5 — Cleanup and cross-links

- Update Obsidian links;
- create or update `docs/README.md`;
- link French and English versions;
- mark obsolete or historical documents explicitly;
- check paths after moving files;
- run a global search for broken links.

## 8. Substitution table for old documents

| Old document | Status | Historical destination | Current replacement |
|---|---|---|---|
| `Architecture_AlirPunkto.md` | obsolete as current architecture | `docs/fr/specifications_historiques/Architecture_AlirPunkto.md` | `docs/fr/architecture/00_vue_d_ensemble.md`, `01_architecture_runtime.md` |
| `Candidature.md` | initial scenario, partly outdated | `docs/fr/specifications_historiques/Candidature.md` | `docs/fr/specifications_fonctionnelles/candidature.md` |
| `Chiffrement de bout en bout.md` | exploratory V2 design note | `docs/fr/specifications_historiques/Chiffrement de bout en bout.md` | `docs/fr/architecture/11_securite.md`, possibly a dedicated ADR |
| `Configuration de la liste des applications.md` | to be rewritten | `docs/fr/specifications_historiques/Configuration de la liste des applications.md` | `docs/fr/architecture/08_applications_tierces.md` |
| `Connexion d'un Membre.md` | too generic | `docs/fr/specifications_historiques/Connexion d'un Membre.md` | `docs/fr/architecture/05_authentification.md`, `docs/fr/specifications_fonctionnelles/connexion.md` |
| `Consultation de la liste des Candidatures.md` | to be rewritten | `docs/fr/specifications_historiques/Consultation de la liste des Candidatures.md` | `docs/fr/specifications_fonctionnelles/liste_candidatures.md` |
| `Consultation de la liste des Membres.md` | to be rewritten | `docs/fr/specifications_historiques/Consultation de la liste des Membres.md` | `docs/fr/specifications_fonctionnelles/liste_membres.md` |
| `Démissionner.md` | flow to confirm | `docs/fr/specifications_historiques/Démissionner.md` | future `docs/fr/specifications_fonctionnelles/desactivation_compte.md`, if retained |
| `Liste des Applications.md` | to be rewritten | `docs/fr/specifications_historiques/Liste des Applications.md` | `docs/fr/specifications_fonctionnelles/applications_tierces.md` |
| `RéinitialisationDuMotDePasse.md` | must be updated according to current code | `docs/fr/specifications_historiques/RéinitialisationDuMotDePasse.md` | `docs/fr/specifications_fonctionnelles/reinitialisation_mot_de_passe.md` |

## 9. Writing rules

New documents must follow these rules:

- write in the present tense;
- clearly separate current behaviour, known limits and planned changes;
- cite the relevant Python modules;
- prefer Mermaid for diagrams;
- avoid long linear scenarios when a state machine or sequence diagram is clearer;
- avoid repeating the same information across documents;
- document important decisions in `architecture_decisions.md`;
- keep domain terms consistent across French and English documentation;
- keep file names stable and readable.

## 10. Completion criteria

The documentation refactoring will be considered complete when:

- old scenarios have been moved into `historical_specifications/`;
- every old scenario has a current replacement or a note explaining why it has not yet been rewritten;
- architecture documentation covers the main components of the current code;
- FR/EN design journals explain the documentation migration;
- documentation README files explain where to find information;
- internal links have been checked;
- tests still pass after documentation moves.
