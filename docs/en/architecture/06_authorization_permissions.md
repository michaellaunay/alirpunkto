# Authorization and permissions

> Status: current documentation.
> Modules: `alirpunkto/models/permissions.py`,
> `alirpunkto/models/model_permissions.py`, `alirpunkto/models/member.py`,
> `alirpunkto/models/candidature.py`.

Three mechanisms currently coexist.

## 1. Minimal Pyramid ACL

`Member` and `Candidature` carry
`__acl__ = [(Allow, 'group:admins', ALL_PERMISSIONS)]`. This ACL is barely
exercised: most views declare no `permission=` and do their own checks.

## 2. Checks inside the views

Views check the session (`logged_in`, presence of `user`) and redirect to
`/login` otherwise; some then restrict by member type (for example
`manage_provider`). This is the mechanism actually in force for page
access.

## 3. Fine-grained per-attribute matrix

This is the most elaborate part: `permissions.Permissions` is an `IntFlag`
(`NONE`, `ACCESS` — field visible but value masked, `READ`, `WRITE`,
`EXECUTE`, `CREATE`, `DELETE`, `TRAVERSE`, `RENAME`, `DELETE_CHILD`,
`ADMIN`). `model_permissions.py` defines frozen matrices
(`MemberPermissions`, `CandidaturePermissions`, field by field through
`MemberDataPermissions`) and the resolution
`get_access_permissions(accessed, accessor)`: rights depend on **the type
and state** of the object being accessed and of the one accessing it. Form
schemas (`schemas/register_form.py`) use it to hide or lock fields
(`read_only_fields`).

## Planned evolution

The documentation refactoring plan and the design journal set the target:
rebuild the Pyramid ACLs as a class hierarchy grounded in this matrix, so
that `permission=` on views and per-attribute rights derive from the same
source. See [architecture_decisions](architecture_decisions.md).
