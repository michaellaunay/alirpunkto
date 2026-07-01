# Plan de refonte de la documentation d'architecture d'AlirPunkto

> Statut : plan d'action documentaire  
> Date : 2026-07-01  
> Langue : français  
> Périmètre : réorganisation et réécriture progressive de la documentation de conception, d'architecture et des scénarios fonctionnels d'AlirPunkto.

## 1. Constat

Les documents de conception actuellement présents dans `docs/fr/` et `docs/en/` proviennent pour une large part du cahier des charges initial et des premières réflexions du projet.

Ils restent utiles pour comprendre la genèse d'AlirPunkto, mais ils ne décrivent plus fidèlement l'architecture actuelle du code.

L'application a désormais évolué vers une architecture plus structurée, comprenant notamment :

- une application Pyramid servie par Waitress ;
- des vues TAL/METAL avec Chameleon ;
- une persistance applicative en ZODB ;
- un annuaire OpenLDAP comme référentiel des comptes et groupes ;
- une extension de schéma LDAP propre à AlirPunkto ;
- une messagerie applicative via Pyramid Mailer et Postfix ;
- une authentification par session Pyramid ;
- une intégration SSO/Keycloak optionnelle ;
- une protection CSRF globale ;
- des cookies de session sécurisés ;
- une pile Docker de déploiement ;
- une pile Docker locale/offline de test ;
- une suite de tests pytest et de tests de non-régression ;
- un outillage de revue de code, notamment `tools/export_sources_for_review.sh`.

Les anciens scénarios restent donc à conserver, mais ils doivent être clairement distingués de la documentation courante.

## 2. Objectifs de la refonte documentaire

La refonte poursuit six objectifs.

1. **Séparer l'historique du courant**  
   Les documents issus du cahier des charges initial doivent être archivés dans un dossier explicite, sans être supprimés.

2. **Documenter l'architecture réelle**  
   La documentation doit refléter le code actuel, les services réellement utilisés, les modules existants et les flux effectivement implémentés.

3. **Créer une documentation maintenable**  
   Les documents doivent être courts, thématiques et reliés entre eux, plutôt qu'une suite de longs scénarios monolithiques.

4. **Faciliter l'arrivée d'un nouveau contributeur**  
   Un développeur doit pouvoir comprendre rapidement les composants, les flux principaux, les modèles, les tests et les points de vigilance.

5. **Préparer les évolutions futures**  
   La documentation doit distinguer clairement l'architecture actuelle, les limites connues et les évolutions cibles, notamment la refonte du mécanisme d'ACL et de permissions.

6. **Assurer la traçabilité**  
   Les documents historiques doivent rester accessibles, mais avec un avertissement clair indiquant qu'ils ne sont plus normatifs.

## 3. Nom proposé pour l'archive des anciens scénarios

Le terme `spec_initiales` est compréhensible mais trop ambigu.

Le nom recommandé est :

```text
docs/fr/specifications_historiques/
docs/en/historical_specifications/
```

Ce nom est explicite, neutre et indique clairement que ces fichiers ont une valeur historique.

Il est préférable à :

- `spec_initiales`, trop court et peu explicite ;
- `legacy_specs`, plus technique mais moins clair pour les lecteurs francophones ;
- `old_docs`, trop vague ;
- `archives`, trop large ;
- `cahier_des_charges_initial`, précis mais trop restrictif, car certains documents sont aussi des notes de conception.

## 4. Nouveau principe de vérité documentaire

À partir de cette refonte, la documentation doit suivre cette hiérarchie :

1. **Le code et les tests sont la source de vérité technique.**
2. **La documentation d'architecture décrit le fonctionnement courant.**
3. **Les spécifications fonctionnelles courantes décrivent les flux métier actuellement retenus.**
4. **Les spécifications historiques décrivent l'intention initiale et ne sont pas normatives.**
5. **Les journaux de conception expliquent les décisions, les changements de direction et les raisons des migrations documentaires.**

Lorsqu'un document historique contredit le code actuel ou la documentation d'architecture, le code actuel et la documentation d'architecture prévalent.

## 5. Nouvelle arborescence proposée

```text
docs/
├── README.md
│
├── fr/
│   ├── Journal de conception.md
│   ├── Plan de refonte documentaire.md
│   │
│   ├── architecture/
│   │   ├── 00_vue_d_ensemble.md
│   │   ├── 01_architecture_runtime.md
│   │   ├── 02_modele_domaine.md
│   │   ├── 03_persistance_zodb.md
│   │   ├── 04_ldap.md
│   │   ├── 05_authentification.md
│   │   ├── 06_autorisations_permissions.md
│   │   ├── 07_messagerie.md
│   │   ├── 08_applications_tierces.md
│   │   ├── 09_taches_periodiques.md
│   │   ├── 10_internationalisation.md
│   │   ├── 11_securite.md
│   │   ├── 12_tests.md
│   │   ├── 13_deploiement_docker.md
│   │   ├── decisions_architecture.md
│   │   └── glossaire.md
│   │
│   ├── specifications_fonctionnelles/
│   │   ├── candidature.md
│   │   ├── connexion.md
│   │   ├── reinitialisation_mot_de_passe.md
│   │   ├── profil_membre.md
│   │   ├── liste_membres.md
│   │   ├── liste_candidatures.md
│   │   └── applications_tierces.md
│   │
│   └── specifications_historiques/
│       ├── README.md
│       ├── Architecture_AlirPunkto.md
│       ├── Candidature.md
│       ├── Chiffrement de bout en bout.md
│       ├── Configuration de la liste des applications.md
│       ├── Connexion d'un Membre.md
│       ├── Consultation de la liste des Candidatures.md
│       ├── Consultation de la liste des Membres.md
│       ├── Démissionner.md
│       ├── Liste des Applications.md
│       └── RéinitialisationDuMotDePasse.md
│
└── en/
    ├── DesignJournal.md
    ├── Documentation Refactoring Plan.md
    │
    ├── architecture/
    │   ├── 00_overview.md
    │   ├── 01_runtime_architecture.md
    │   ├── 02_domain_model.md
    │   ├── 03_zodb_persistence.md
    │   ├── 04_ldap.md
    │   ├── 05_authentication.md
    │   ├── 06_authorization_permissions.md
    │   ├── 07_email.md
    │   ├── 08_third_party_applications.md
    │   ├── 09_periodic_tasks.md
    │   ├── 10_internationalization.md
    │   ├── 11_security.md
    │   ├── 12_testing.md
    │   ├── 13_docker_deployment.md
    │   ├── architecture_decisions.md
    │   └── glossary.md
    │
    ├── functional_specifications/
    │   ├── candidature.md
    │   ├── login.md
    │   ├── password_reset.md
    │   ├── member_profile.md
    │   ├── member_list.md
    │   ├── candidature_list.md
    │   └── third_party_applications.md
    │
    └── historical_specifications/
        ├── README.md
        └── ...
```

## 6. Avertissement à placer dans les spécifications historiques

Chaque dossier historique doit contenir un `README.md` avec un avertissement clair.

Texte proposé pour `docs/fr/specifications_historiques/README.md` :

```markdown
# Spécifications historiques

Ce dossier contient les scénarios et documents de conception rédigés au lancement du projet AlirPunkto.

Ils sont conservés pour mémoire, traçabilité et compréhension de l'intention initiale du projet.

Ces documents ne décrivent plus nécessairement l'état actuel de l'application et ne doivent pas être utilisés comme documentation normative.

La documentation courante se trouve dans :

- `docs/fr/architecture/`
- `docs/fr/specifications_fonctionnelles/`

En cas de divergence, le code actuel, les tests et la documentation d'architecture courante prévalent.
```

## 7. Documents à créer en priorité

La refonte doit être progressive. L'ordre recommandé est le suivant.

### Phase 1 — Cadre documentaire

- `docs/fr/Plan de refonte documentaire.md`
- `docs/en/Documentation Refactoring Plan.md`
- `docs/fr/specifications_historiques/README.md`
- `docs/en/historical_specifications/README.md`
- mise à jour de `docs/fr/Journal de conception.md`
- mise à jour de `docs/en/DesignJournal.md`

### Phase 2 — Architecture actuelle

Créer les documents d'architecture qui décrivent le code actuel :

1. `00_vue_d_ensemble.md`
2. `01_architecture_runtime.md`
3. `02_modele_domaine.md`
4. `03_persistance_zodb.md`
5. `04_ldap.md`
6. `05_authentification.md`
7. `06_autorisations_permissions.md`
8. `07_messagerie.md`
9. `08_applications_tierces.md`
10. `09_taches_periodiques.md`
11. `10_internationalisation.md`
12. `11_securite.md`
13. `12_tests.md`
14. `13_deploiement_docker.md`

### Phase 3 — Spécifications fonctionnelles courantes

Réécrire les scénarios fonctionnels selon l'état réel ou cible proche du projet :

- candidature ;
- connexion ;
- réinitialisation du mot de passe ;
- consultation et modification du profil ;
- gestion des membres ;
- gestion des candidatures ;
- configuration des applications tierces ;
- démission ou désactivation du compte, si ce flux est encore prévu.

### Phase 4 — Décisions d'architecture

Créer un document de décisions d'architecture.

Premières décisions à documenter :

- usage de Pyramid ;
- usage de ZODB ;
- usage d'OpenLDAP comme référentiel d'identités ;
- usage d'un schéma LDAP spécifique ;
- usage de Chameleon/TAL/METAL ;
- usage de Postfix ;
- usage de Docker ;
- stratégie de tests ;
- modèle actuel de permissions ;
- cible de refonte des ACL par hiérarchie de classes.

### Phase 5 — Nettoyage et liens croisés

- Mettre à jour les liens Obsidian ;
- créer ou mettre à jour `docs/README.md` ;
- ajouter les liens vers les versions françaises et anglaises ;
- indiquer les documents obsolètes ou historiques ;
- vérifier les chemins après déplacement ;
- lancer une recherche globale pour détecter les liens cassés.

## 8. Tableau de substitution des anciens documents

| Ancien document | Statut | Destination historique | Remplacement courant |
|---|---|---|---|
| `Architecture_AlirPunkto.md` | obsolète comme architecture courante | `docs/fr/specifications_historiques/Architecture_AlirPunkto.md` | `docs/fr/architecture/00_vue_d_ensemble.md`, `01_architecture_runtime.md` |
| `Candidature.md` | scénario initial partiellement dépassé | `docs/fr/specifications_historiques/Candidature.md` | `docs/fr/specifications_fonctionnelles/candidature.md` |
| `Chiffrement de bout en bout.md` | réflexion V2 / exploratoire | `docs/fr/specifications_historiques/Chiffrement de bout en bout.md` | `docs/fr/architecture/11_securite.md`, éventuellement ADR dédié |
| `Configuration de la liste des applications.md` | à réécrire | `docs/fr/specifications_historiques/Configuration de la liste des applications.md` | `docs/fr/architecture/08_applications_tierces.md` |
| `Connexion d'un Membre.md` | trop générique | `docs/fr/specifications_historiques/Connexion d'un Membre.md` | `docs/fr/architecture/05_authentification.md`, `docs/fr/specifications_fonctionnelles/connexion.md` |
| `Consultation de la liste des Candidatures.md` | à réécrire | `docs/fr/specifications_historiques/Consultation de la liste des Candidatures.md` | `docs/fr/specifications_fonctionnelles/liste_candidatures.md` |
| `Consultation de la liste des Membres.md` | à réécrire | `docs/fr/specifications_historiques/Consultation de la liste des Membres.md` | `docs/fr/specifications_fonctionnelles/liste_membres.md` |
| `Démissionner.md` | flux à confirmer | `docs/fr/specifications_historiques/Démissionner.md` | futur `docs/fr/specifications_fonctionnelles/desactivation_compte.md` si retenu |
| `Liste des Applications.md` | à réécrire | `docs/fr/specifications_historiques/Liste des Applications.md` | `docs/fr/specifications_fonctionnelles/applications_tierces.md` |
| `RéinitialisationDuMotDePasse.md` | à mettre à jour selon le code actuel | `docs/fr/specifications_historiques/RéinitialisationDuMotDePasse.md` | `docs/fr/specifications_fonctionnelles/reinitialisation_mot_de_passe.md` |

## 9. Règles de rédaction

Les nouveaux documents doivent respecter les règles suivantes :

- écrire au présent ;
- distinguer clairement l'existant, les limites et les évolutions prévues ;
- citer les modules Python concernés ;
- préférer Mermaid pour les diagrammes ;
- éviter les longs scénarios linéaires quand une machine à états ou un diagramme de séquence est plus lisible ;
- éviter de répéter les mêmes informations dans plusieurs documents ;
- documenter les décisions importantes dans `decisions_architecture.md` ;
- conserver les termes métier français dans la documentation française ;
- garder des noms de fichiers stables et lisibles.

## 10. Critères de fin

La refonte documentaire sera considérée comme terminée lorsque :

- les anciens scénarios auront été déplacés dans `specifications_historiques/` ;
- chaque ancien scénario aura un remplacement courant ou une note expliquant pourquoi il n'est pas encore réécrit ;
- la documentation d'architecture couvrira les principaux composants du code actuel ;
- les journaux de conception FR/EN expliqueront la migration documentaire ;
- les README de documentation expliqueront où trouver les informations ;
- les liens internes auront été vérifiés ;
- les tests continueront de passer après les déplacements documentaires.
