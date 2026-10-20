# The member profile

Covers issues #55 (field matrix), #123 (view frame), #149
(administrator card), #201 and #249 (visibility), #263 and #270 (public
card content).

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
number, e-mail (#249), role, CBM with its date, departure date and
reason. Nothing else is transmitted (no IBAN, no civil identity),
viewing does not change the member's state, and no submission on this
page can end in a write.

The **financial facts** of a Cooperator (shares owned, yearly
contribution end date — #75) are not changed through this card: they
have their own administrative write path, described in
[financial_status](financial_status.md) (#267).

## What other members see (issues #249, #263, #270)

Every logged-in member browses the member directory and can open
another member's **public card** — never their form: pseudonym,
**presentation text** and **avatar** (#270, to get an idea of who the
person is), role in the Cooperative (#263), CBM and its update date. No
e-mail, no user number, no IBAN, no civil identity: those stay on the
administrator's card. Member-to-member interactions happen on the shared
workspace.
