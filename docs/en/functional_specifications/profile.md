# The member profile

Covers issues #55 (field matrix), #123 (view frame), #149
(administrator card) and #201 (visibility).

## One's own page

Any logged-in member opening "Modify my data" lands directly on
**their** profile: the "Your profile" title, the introduction, then —
outside the form — **the groups they belong to** (translated labels)
and, for a Cooperator or assimilated, **their role** in the
Cooperative. The form follows the matrix below and ends with the
**Submit** and **Cancel** buttons; cancelling reloads the profile clear
of any input (no directory access before the redirect).

## The field matrix (issue #55)

| Element | Every member | Cooperator or assimilated |
|---|---|---|
| Presentation text, avatar, e-mail, languages | view + edit | view + edit |
| IBAN | — | view + edit |
| Pseudonym, user number, groups | view | view |
| Identity (given names, family names, birth), nationality | — | view |
| CBM and its update time, shares, contribution end date, role | — | view |
| Erasure date (#54) | never | never |

"Cooperator or assimilated" means the members of the six cooperator
groups (candidates missing complements, sanctioned included). Changing
the e-mail goes through the confirmation link
([e-mail change](../architecture/07_email.md)); changing the password
through the dedicated fields. A member whose resignation is pending
accesses their profile normally — that is where "Cancel my deactivation
request" lives.

## Consultation by an administrator (issue #149)

An administrator opening another member's profile gets a **read-only
card** — never the form: pseudonym, presentation text, avatar, user
number, role, CBM with its date, departure date and reason. Nothing
else is transmitted (no e-mail, no IBAN, no civil identity), viewing
does not change the member's state, and no submission can end in a
write.

## What others never see (issue #201)

A non-administrator member has **no access** to another member's
profile: no member list, no consultation — member-to-member
interactions happen on the shared workspace.
