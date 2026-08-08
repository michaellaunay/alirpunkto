# Audit externe du sous-système locale (ChatGPT) — 8 août 2026

**Provenance.** Audit thématique externe (ChatGPT, à la demande de
Michaël Launay) du répertoire `alirpunkto/locale` et de l'outillage
de traduction, sur le commit `f01d0eb5`. Reproduit ici intégralement
et sans modification. Les corrections apportées en réponse sont
consignées au chapitre 10 (Internationalisation) : train 0098 —
couverture POT complète des 33 catalogues (651 entrées de fallback
anglais non-fuzzy), recompilation des 33 `.mo`, découverte de
locales par répertoires seuls, verrous CI `test_locale_completeness`
avec cliquets sur les dettes fuzzy/vides. Les décisions de
gouvernance (registre unique, sort des huit locales non proposées,
niveaux de support) restent ouvertes au mainteneur.

---

# Audit complet du répertoire `alirpunkto/locale`

**Dépôt :** `michaellaunay/alirpunkto`
**Branche :** `master`
**État courant :** `f01d0eb5fa7061d0140458814de69ec7dd78cadc`
**Périmètre :** catalogues gettext, fichiers `.pot/.po/.mo`, templates localisés `.pt`, choix des langues, fallback, outillage de traduction et tests.

## 1. Conclusion générale

Le système d'internationalisation d'AlirPunkto est **techniquement bien structuré**, mais son contenu linguistique est actuellement très hétérogène.

Il existe quatre états différents que l'application mélange aujourd'hui :

1. des traductions réellement disponibles dans la langue cible ;
2. des traductions `fuzzy`, souvent encore rédigées en anglais ;
3. des `msgstr` anglais non `fuzzy`, utilisés volontairement comme fallback ;
4. des clés totalement absentes de certains catalogues, qui risquent d'afficher directement leur identifiant symbolique.

À cela s'ajoute une cinquième situation pour les mails :

5. des templates `.pt` qui n'existent simplement pas dans certaines langues et retombent sur le template anglais.

Le problème principal n'est donc pas seulement « certaines traductions manquent ». Il manque aujourd'hui une **définition unique et testée de ce que signifie "langue supportée par AlirPunkto"**.

### Évaluation

**Infrastructure i18n : 8/10**

**Qualité et complétude des traductions : 5/10**

**Cohérence globale du sous-système locale : 5,5/10**

---

# 2. Les langues présentes sur disque

Le dépôt contient actuellement **33 répertoires de locale** :

```text
be  bg  bs  cs  da  de  el  en  eo  es  et
fi  fr  ga  hr  hu  is  it  lt  lv  mt  nl
no  pl  pt  ro  sk  sl  sq  sr  sv  tr  uk
```

Chaque langue utilise la structure `alirpunkto/locale/<lang>/LC_MESSAGES/` avec au minimum le catalogue `alirpunkto.po`, généralement son `.mo`, et éventuellement des templates `.pt`. Le fichier canonique est `alirpunkto/locale/alirpunkto.pot`.

---

# 3. Premier problème majeur : il existe trois listes différentes de langues

## 3.1 Le disque dit : 33 langues

## 3.2 L'interface utilisateur dit : 25 langues

Le formulaire d'inscription et de profil construit sa liste à partir de `EUROPEAN_LOCALES` qui ne contient que 25 langues (`eo bg cs da de et el en es fr ga hr it lv lt hu mt nl pl pt ro sk sl fi sv`).

Il existe donc **8 locales présentes sur disque mais non proposées comme langue préférée** :

```text
be  bs  is  no  sq  sr  tr  uk
```

C'est une incohérence fonctionnelle.

---

# 4. `AVAILABLE_LANGUAGES` contient vraisemblablement deux fois `en`

La fonction `get_locales()` ajoutait `+ ['en']` alors que `locale/en/` existe déjà, et filtrait seulement `not x.endswith('.pot')` au lieu de vérifier `os.path.isdir(...)`. Un fichier parasite placé sous `locale/` pouvait donc devenir une prétendue langue.

### Correction

La découverte par répertoire ne devrait plus servir de registre fonctionnel. Il faut une source explicite unique (`SUPPORTED_LOCALES`) et dériver toutes les autres listes de celle-ci.

---

# 5. Quatrième liste implicite : l'outil de traduction

`tools/translate.sh` possédait sa propre liste codée en dur, contenant notamment `mk = Macedonian` alors que `alirpunkto/locale/mk/` n'existe pas.

| Source                |          Nombre / particularité |
| --------------------- | ------------------------------: |
| Répertoires `locale/` |                              33 |
| `EUROPEAN_LOCALES`    |                              25 |
| `AVAILABLE_LANGUAGES` |               33 + doublon `en` |
| `translate.sh`        | 33 cibles, dont `mk` inexistant |

Un simple ajout de langue nécessite actuellement de penser à plusieurs endroits indépendants.

---

# 6. État du catalogue canonique `.pot`

Le POT n'est pas un template gettext conventionnel : ses premières entrées possèdent des traductions anglaises (`msgid "welcome" / msgstr "Welcome"`) tandis que ses entrées récentes sont vides. Le POT a **deux sémantiques mélangées** : anciennement catalogue anglais, récemment vrai template. Un POT canonique devrait avoir tous les `msgstr` vides, l'anglais vivant exclusivement dans `locale/en/LC_MESSAGES/alirpunkto.po`. Dette pour l'outillage automatique.

---

# 7. Le grand rattrapage historique n'est plus suffisant

Un commit de synchronisation précédent avait ramené les catalogues à 282 msgid communs (31 catalogues sur 33 incomplets ; l'espéranto manquait 217 clés sur 282 ; clés ajoutées en anglais `fuzzy`). De nouvelles chaînes ont depuis été ajoutées sans nouvelle synchronisation générale.

---

# 8. Au moins 16 clés sont aujourd'hui totalement absentes de 31 langues

## 8.1 Profil utilisateur : 3 clés

`your_profile_title`, `your_profile_introduction`, `cancel_button` — seulement dans le POT, `en` et `fr`.

# 9. Groupes du membre : 13 clés supplémentaires manquent

`your_groups_label` et les douze `group_label_*` — même périmètre.

### Bilan certain

**16 msgid symboliques totalement absents dans 31 langues.** Une chaîne telle que `group_label_community` peut se retrouver affichée telle quelle à l'utilisateur.

### Priorité : P0 i18n

Ces 16 clés doivent immédiatement être synchronisées dans les 31 catalogues. Même un fallback anglais explicite serait préférable au msgid brut.

---

# 10. Les entrées `fuzzy` restent nombreuses

Exemples en allemand et en espagnol sur les fonctions de prestataire (`provider_role_activated`, `invalid_field_value`, etc., en anglais avec le flag `fuzzy`).

### Attention au comportement gettext

Une traduction `fuzzy` n'est pas simplement « probablement mauvaise » : par défaut, `msgfmt` **ne l'intègre pas dans le `.mo`**. Le `msgstr` anglais peut ne jamais atteindre le runtime.

### Il faut choisir entre deux états

Soit une vraie traduction, soit temporairement l'anglais **sans** `fuzzy`. Conserver `#, fuzzy` avec un msgstr anglais est le pire compromis lorsque le msgid est symbolique.

---

# 11. L'espéranto est dans une situation critique

Le fichier `eo` contient de véritables traductions historiques (`msgid "seven" / msgstr "sep"`), mais un très grand bloc central reste anglais/fuzzy, touchant des fonctions fondamentales : accueil, authentification, validation d'adresse, défi anti-robot, mot de passe, inscription, formulaires.

### Classification

**Espéranto : traduction expérimentale / très incomplète.** Or elle fait partie des langues réellement proposées par `EUROPEAN_LOCALES` — incohérent avec l'image d'une langue pleinement supportée.

---

# 12. Autre phénomène : anglais non `fuzzy`

Lors du passage aux msgid symboliques, 34 anciennes chaînes littérales et plusieurs sujets de mails ont été propagés dans les 31 catalogues avec leur traduction anglaise **sans flag fuzzy** — un fallback volontaire et raisonnable, mais encore largement présent (ex. `application_workspace_name` en allemand et en espagnol). Une page allemande peut aujourd'hui mélanger du bon allemand historique, des fonctions récentes en anglais, éventuellement une clé symbolique brute, et un template de mail entièrement anglais.

---

# 13. Même le français n'est pas totalement complet

Le français est de très loin l'une des meilleures locales, mais contient au moins des entrées vides (`cooperator_number_required`, `cooperative_behaviour_mark_update_required`).

---

# 14. État des templates de mails

Les templates d'approbation/refus existent dans 7 langues (`de en es fr it nl pl`) ; `send_candidature_pending_email.pt` et le cycle désabonnement/effacement n'existent qu'en `en`/`fr` — fallback anglais pour les autres. Cette politique est documentée et encodée dans les tests.

# 15. Les tests actuels ne vérifient pas la complétude des templates

Le test des templates teste « les templates qui existent » : un template absent est ignoré. Il manque une assertion de **matrice de couverture**.

# 16. L'outil de traduction et la politique actuelle se contredisent

Politique A (application) : une langue peut être supportée partiellement et retomber sur l'anglais. Politique B (outil) : chaque langue cible doit reproduire toute la structure anglaise. Recommandation : **politique B pour les langues annoncées comme supportées**.

# 17. Les `.mo` constituent un autre risque de désynchronisation

L'application lit le `.mo`, pas le `.po`. Sans recompilation, un PO corrigé laisse le runtime ancien. Aucun garde-fou générique PO↔MO n'existait dans la CI.

---

# 18. État qualitatif par groupe de langues

| Groupe                               | Langues                                              | État |
| ------------------------------------ | ---------------------------------------------------- | ---- |
| Référence                            | `en`                                                 | source fonctionnelle |
| Très avancée                         | `fr`                                                 | très bonne couverture, quelques entrées vides |
| Principales historiques              | `de es it nl pl`                                     | traductions historiques importantes, dette anglaise récente |
| Autres langues proposées             | `bg cs da el et fi ga hr hu lt lv mt pt ro sk sl sv` | couverture ancienne variable, forte dette anglaise récente |
| Cas critique proposé                 | `eo`                                                 | très forte dette fuzzy/anglais |
| Locales présentes mais non proposées | `be bs is no sq sr tr uk`                            | incohérentes avec le registre UI |
| Fantôme de l'outil                   | `mk`                                                 | annoncé par `translate.sh`, aucun répertoire |

---

# 19. Les cinq états qu'un audit automatique doit distinguer

**A — Traduit** (`msgstr "Annuler"`) : OK. **B — Fallback anglais explicite** : fonctionnel, non traduit. **C — Fuzzy** : non valide pour la production. **D — Vide** : non traduit. **E — Clé absente** : erreur de synchronisation — devrait être interdite par la CI.

# 20. Proposition de niveaux de support

**Tier 1** (100 % clés, 0 fuzzy, 0 vide, tous templates, `.mo` à jour) : actuellement `en`, `fr` s'en approche. **Tier 2** (toutes clés présentes, fallback anglais accepté) : `de es it nl pl` à portée. **Tier 3** (expérimental) : les autres.

# 21–24. Corrections P0 recommandées

**P0.1** — registre unique des langues (`SUPPORTED_LOCALES`), dont dériver `AVAILABLE_LANGUAGES`, le formulaire, `translate.sh`, les tests. **P0.2** — décider du sort des huit locales orphelines. **P0.3** — synchroniser immédiatement les 31 catalogues (objectif : plus jamais de msgid symbolique affichable). **P0.4** — recompiler les 33 `.mo` (compilation en échec si catalogue invalide).

# 25–27. Corrections P1

**0 fuzzy autorisé dans une release** (traduire réellement, ou anglais explicite sans fuzzy). Détecter automatiquement l'anglais dans les locales (statistiques par langue, allowlist des termes identiques). Compléter les templates (Tier 1 : `set(locale/en/*.pt) == set(locale/<lang>/*.pt)`).

# 28. Test CI à ajouter : `test_locale_completeness.py`

Unicité du registre ; répertoire existant par langue ; aucun répertoire inconnu ; aucun `mk` fantôme ; **toutes les clés POT dans tous les PO** ; aucune clé obsolète ; aucun fuzzy Tier 1 ; aucune vide Tier 1 ; comptage des fallbacks anglais ; matrice des templates ; compilation de chaque PO ; cohérence PO/MO. L'assertion essentielle : `set(po_msgids) == set(pot_msgids)` pour chaque locale — elle aurait empêché les 16 clés de rester absentes.

# 29. Le script de traduction actuel est une bonne base

POT canonique, anglais/français comme contexte, traductions réutilisées, fuzzy traités, placeholders préservés, synchronisation des templates. Ce qui manque : faire de cette synchronisation **une propriété vérifiée du dépôt**.

# 30. Ordre de remise en état recommandé

Phase 1 cohérence structurelle (registre, doublon, `mk`, orphelines, synchronisation, `.mo`) ; Phase 2 test de complétude en CI ; Phase 3 langues prioritaires (`fr de es it nl pl`) ; Phase 4 autres langues proposées ; Phase 5 passe espéranto complète ; Phase 6 locales non proposées.

# 31. Tableau final des anomalies

| Anomalie                                          | Sévérité  |
| ------------------------------------------------- | --------- |
| 16 clés récentes absentes de 31 catalogues        | **P0**    |
| 3 sources de vérité différentes pour les langues  | **P0**    |
| 8 répertoires de langue non proposés par l'UI     | **P0/P1** |
| `mk` dans l'outil mais absent du projet           | **P1**    |
| doublon `en` dans `AVAILABLE_LANGUAGES`           | **P1**    |
| nombreuses traductions anglaises dans les locales | **P1**    |
| entrées fuzzy anglaises encore présentes          | **P1**    |
| espéranto très incomplet                          | **P1**    |
| français contenant encore des `msgstr` vides      | **P1/P2** |
| templates incomplets selon les langues            | **P1/P2** |
| tests qui tolèrent les templates absents          | **P1**    |
| absence de contrôle général PO ↔ MO trouvé        | **P1**    |
| POT mélange template et catalogue anglais         | **P2**    |
| métadonnées du POT anciennes                      | **P2**    |

# 32. Verdict

Le moteur d'internationalisation d'AlirPunkto est **meilleur que l'état des traductions ne le laisse penser**. Le problème est essentiellement devenu un problème **de gouvernance des traductions** : passer de « un répertoire existe pour cette langue » à « cette langue possède un niveau de support mesurable et vérifié par la CI ». La première action indispensable : un audit automatique reproductible des 33 catalogues (msgid totaux, traduits, anglais identiques, fuzzy, vides, absents, obsolètes, templates, `.mo`, niveau de support).
