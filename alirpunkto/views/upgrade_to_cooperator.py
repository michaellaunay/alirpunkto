"""Upgrade an Ordinary Member to Cooperator (issue #7).

An Ordinary Member, convinced by the Community, may upgrade to Cooperator:
a button on the home page leads to a short identity form — the four fields
the verifiers compare with the ID document — then the existing Cooperator
registration flow takes over: the candidature enters UNIQUE_DATA, the
verifiers are drawn and convened, the vote runs, and on approval the LDAP
entry of the member is updated in place (type, identity attributes, group)
instead of being created. The pseudonym is kept identical by construction:
it is copied from the member and never asked again.
"""
from __future__ import annotations

import logging

import colander
import deform
from deform import ValidationFailure, schema
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

from alirpunkto.constants_and_globals import (
    _,
    CANDIDATURE_OID,
    log,
)
from alirpunkto.models.candidature import Candidature, CandidatureStates
from alirpunkto.models.member import MemberDatas, MemberTypes
from alirpunkto.schemas.register_form import RegisterForm
from alirpunkto.utils import (
    get_candidatures,
    get_member_by_oid,
    is_valid_unique_identity,
)

IDENTITY_FIELDS = ('fullname', 'fullsurname', 'birthdate', 'nationality')

# Candidature states in which an upgrade candidature is still running: a
# member with one of these must resume it instead of opening a second one.
_RUNNING_STATES = (
    CandidatureStates.UNIQUE_DATA,
    CandidatureStates.PENDING,
)


class UpgradeIdentityForm(schema.CSRFSchema):
    """The four identity fields, cloned from RegisterForm so the labels,
    descriptions and widgets stay the single source of truth — but required,
    since the whole point of the upgrade is the identity verification."""


def _upgrade_identity_schema(request):
    register_form = RegisterForm()
    upgrade = UpgradeIdentityForm()
    for name in IDENTITY_FIELDS:
        node = register_form.get(name).clone()
        node.missing = colander.required
        upgrade.add(node)
    return upgrade.bind(request=request)


def _base_context(request, **extra):
    settings = getattr(request.registry, 'settings', {}) or {}
    context = {
        'logged_in': request.session.get('logged_in', False),
        'site_name': settings.get('site_name'),
        'domain_name': settings.get('domain_name'),
        'organization_details': settings.get('organization_details'),
        'form': None,
        'member': None,
        'error': None,
    }
    context.update(extra)
    return context


@view_config(
    route_name='upgrade_to_cooperator',
    renderer='alirpunkto:templates/upgrade_to_cooperator.pt'
)
def upgrade_to_cooperator(request):
    """Show the identity form and, on submit, open the upgrade candidature."""
    if not request.session.get('logged_in') or not request.session.get('user'):
        request.session.flash(_('user_not_logged_in'), 'error')
        return HTTPFound(location=request.route_url('home'))

    user = request.session.get('user')
    if isinstance(user, str):
        import json
        try:
            user = json.loads(user)
        except (TypeError, ValueError):
            user = {}
    member_oid = user.get('oid') if isinstance(user, dict) else None
    member = get_member_by_oid(member_oid, request) if member_oid else None
    if member is None:
        return _base_context(request, error=_('unknown_member'))

    if member.type != MemberTypes.ORDINARY:
        return _base_context(
            request, member=member,
            error=_('upgrade_only_ordinary_error'))

    candidatures = get_candidatures(request)
    for candidature in candidatures.values():
        if (getattr(candidature, 'existing_member_oid', None) == member.oid
                and candidature.candidature_state in _RUNNING_STATES):
            # Resume the running upgrade instead of opening a second one.
            request.session[CANDIDATURE_OID] = candidature.oid
            return HTTPFound(location=request.route_url('register'))

    schema_ = _upgrade_identity_schema(request)
    form = deform.Form(schema_, buttons=('submit',))

    if 'submit' in request.POST:
        try:
            appstruct = form.validate(list(request.POST.items()))
        except ValidationFailure as e:
            return _base_context(request, member=member, form=e.render())

        # Same Quarantine-aware identity check as the registration flow
        # (issue #54).
        identity_error = is_valid_unique_identity(
            appstruct['fullname'], appstruct['fullsurname'],
            appstruct['birthdate'])
        if identity_error:
            return _base_context(request, member=member,
                                 form=form.render(appstruct=appstruct),
                                 error=identity_error['error'])

        candidature = Candidature()
        candidature.type = MemberTypes.COOPERATOR
        candidature.email = member.email
        # The pseudonym is kept identical by construction (issue #7): copied
        # from the member, never asked, never editable.
        candidature.pseudonym = member.pseudonym
        candidature.existing_member_oid = member.oid
        member_data = getattr(member, 'data', None)
        candidature.data = MemberDatas(
            password='',
            fullname=appstruct['fullname'],
            fullsurname=appstruct['fullsurname'],
            birthdate=appstruct['birthdate'],
            nationality=appstruct['nationality'],
            lang1=getattr(member_data, 'lang1', None) or 'en',
            lang2=getattr(member_data, 'lang2', None),
            lang3=getattr(member_data, 'lang3', None),
            description=getattr(member_data, 'description', None),
        )
        candidature.candidature_state = CandidatureStates.UNIQUE_DATA
        candidatures[candidature.oid] = candidature
        candidatures.monitored_members[candidature.oid] = candidature
        request.session[CANDIDATURE_OID] = candidature.oid
        log.info(
            f"Upgrade candidature {candidature.oid} opened for member "
            f"{member.oid} ({member.pseudonym})"
        )
        return HTTPFound(location=request.route_url('register'))

    return _base_context(request, member=member, form=form.render())
