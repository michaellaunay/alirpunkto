# Autorisations et permissions

> Statut : documentation courante.
> Modules : `alirpunkto/models/permissions.py`,
> `alirpunkto/models/model_permissions.py`, `alirpunkto/models/member.py`,
> `alirpunkto/models/candidature.py`.

Trois mécanismes coexistent aujourd'hui.

## 1. ACL Pyramid minimale

`Member` et `Candidature` portent
`__acl__ = [(Allow, 'group:admins', ALL_PERMISSIONS)]`. Cette ACL n'est
guère exploitée : la plupart des vues ne déclarent pas de `permission=` et
font leurs propres contrôles.

## 2. Contrôles dans les vues

Les vues vérifient la session (`logged_in`, présence de `user`) et
redirigent vers `/login` sinon ; certaines restreignent ensuite selon le
type du membre (par exemple `manage_provider`). C'est le mécanisme
réellement en vigueur pour l'accès aux pages.

## 3. Matrice fine par attribut

C'est la partie la plus élaborée : `permissions.Permissions` est un
`IntFlag` (`NONE`, `ACCESS` — champ visible mais valeur masquée, `READ`,
`WRITE`, `EXECUTE`, `CREATE`, `DELETE`, `TRAVERSE`, `RENAME`,
`DELETE_CHILD`, `ADMIN`). `model_permissions.py` définit des matrices gelées
(`MemberPermissions`, `CandidaturePermissions`, champ par champ via
`MemberDataPermissions`) et la résolution
`get_access_permissions(accessed, accessor)` : les droits dépendent **du
type et de l'état** de l'objet consulté et de celui qui consulte. Les
schémas de formulaires (`schemas/register_form.py`) s'en servent pour
masquer ou verrouiller les champs (`read_only_fields`).

## Évolution prévue

Le plan de refonte documentaire et le journal de conception fixent la
cible : refondre les ACL Pyramid par une hiérarchie de classes s'appuyant
sur cette matrice, afin que `permission=` sur les vues et les droits par
attribut procèdent de la même source. Voir
[decisions_architecture](decisions_architecture.md).
