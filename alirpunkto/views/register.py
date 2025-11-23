# description: Register view
#   A candidate submits their application through the "register" view on the site.
#   The site verifies that the candidate is not already registered.
#   The site collects their information and sends them an email to confirm their application submission.
#   The site creates an application object and randomly selects 3 members from the LDAP members if possible, otherwise the administrator.
#   The site invites voters to vote for or against the application.
# author: Michaël Launay
# date: 2023-06-15

import datetime
from typing import Dict, Optional,Union
import deform
from deform import ValidationFailure
from pyramid.view import view_config
from pyramid.request import Request
from alirpunkto.schemas.register_form import RegisterForm
from alirpunkto.models.candidature import (
    Candidature, CandidatureStates, 
    Voter,
)
from alirpunkto.models.member import (
    MemberTypes,
    MemberDatas,
    EmailSendStatus,
)
from alirpunkto.constants_and_globals import (
    _,
    MAIL_SIGNATURE,
    log,
    ADMIN_EMAIL,
    LDAP_TIME_FORMAT,
    LDAP_TIME_LENGTH,
    LDAP_DATE_LENGTH,
    LDAP_DEFAULT_HOUR,
    VERIFIER_VOTE_DEADLINE_DAYS,
)
from pyramid.i18n import Translator
from pyramid.path import AssetResolver

INFORM_VERIFIER_TEMPLATE = 'locale/{lang}/LC_MESSAGES/inform_verifiers.pt'
VERIFIER_TEMPLATE_RESOLVER = AssetResolver('alirpunkto')
from ..utils import (
    get_candidatures,
    get_member_by_oid,
    is_valid_email,
    register_user_to_ldap,
    is_valid_password, is_valid_unique_pseudonym, random_voters,
    send_validation_email,
    send_confirm_validation_email,
    send_candidature_state_change_email,
    send_email,
    retrieve_candidature,
)
from alirpunkto.models.model_permissions import get_access_permissions
from alirpunkto.models.permissions import Permissions

@view_config(route_name='register',
             renderer='alirpunkto:templates/register.pt')
def register(request: Request) -> Dict:
    """Register a new candidate via the web view.

    This view handles the submission of a candidate's registration application.
    It ensures the candidate is not already registered, collects their
    information, sends a confirmation email, creates a candidature object,
    and selects random voters for the application.

    Parameters:
    - request (Request): The pyramid request object.

    Returns:
    - Dict: A dictionary with candidature details and any error messages.
    
    """
    # Attempt to retrieve existing candidature from session or URL
    candidature, error = retrieve_candidature(request)

    if error:
        return error

    # Handle the current state of the candidature process
    return _handle_candidature_state(request, candidature)

def _handle_candidature_state(
        request:Request,
        candidature:Candidature
    ) -> Dict:
    """Handle the candidature state and return the appropriate view.

    Parameters:
    - request (Request): The pyramid request object.
    - candidature (Candidature): The candidature object.

    Returns:
    - Dict: A dictionary with the rendered state view.
    """
    result = None
    if request.method == 'POST':
        log.debug(f"Handling candidature state: request POST: {request.POST}")
    else:
        log.debug(f"Handling candidature state: request method: {request.method}")
    log.debug(f"Handling candidature state of id: {id(candidature)}, state:{candidature.candidature_state}, oid:{getattr(candidature,'oid', 'Not defined')}, type: {getattr(candidature, 'type', 'Not defined')}")
    match candidature.candidature_state:
        case CandidatureStates.DRAFT:
            result = handle_draft_state(request, candidature)
        case CandidatureStates.EMAIL_VALIDATION:
            result = handle_email_validation_state(request, candidature)
        case CandidatureStates.CONFIRMED_HUMAN:
            result = handle_confirmed_human_state(request, candidature)
        case CandidatureStates.UNIQUE_DATA:
            result = handle_unique_data_state(request, candidature)
        case CandidatureStates.PENDING:
            result = handle_pending_state(request, candidature)
        case CandidatureStates.APPROVED:
            result = handle_pending_state(request, candidature)
        case CandidatureStates.REFUSED:
            result = handle_pending_state(request, candidature)
        case _:
            log.error("Candidature state not handled: %s", candidature.candidature_state)
            result = handle_default_state(request, candidature)
    result["site_name"] = request.registry.settings.get('site_name')
    result["domain_name"] = request.registry.settings.get('domain_name')
    result["organization_details"] = request.registry.settings.get('organization_details')
    return result

def handle_draft_state(request: Request, candidature: Candidature) -> dict:
    """
    Process draft state of a candidature with form submission.

    Validates email and choice, generates a math challenge,
    sends a validation email, and updates the candidature state.

    Args:
        request (Request): The Pyramid request object.
        candidature (Candidature): The draft state candidature.

    Returns:
        dict: Candidature data and error messages or HTTPFound on success.
    """
    log.debug(f"Handling draft state for candidature id:{id(candidature)}, oid:{candidature.oid}")
    if 'submit' in request.POST:
        email = request.params['email']
        choice = request.params['choice']

        error = validate_candidature_choice_and_email(
            email, choice, request, candidature
        )
        if error:
            log.debug(f"Handling draft state for candidature error {error}")
            return error
        from alirpunkto.utils import generate_math_challenges # Due to the precedence of unit test fixture imports, we need to import it here
        candidature.challenge = generate_math_challenges(request)

        if not attempt_send_validation_email(request, candidature):
            log.debug(f"Handling draft state for candidature email_not_sent")
            return {
                'candidature': candidature,
                'MemberTypes': MemberTypes,
                'error': _('email_not_sent')
            }

        candidature.candidature_state = CandidatureStates.EMAIL_VALIDATION
        return commit_candidature_changes(request, candidature)

    return {'candidature': candidature, 'MemberTypes': MemberTypes}

def validate_candidature_choice_and_email(
        email: str, choice: str, 
        request: Request, 
        candidature: Candidature
    ) -> dict:
    """
    Validate email and choice for candidature.

    Args:
        email (str): Candidate's email.
        choice (str): Candidature type choice.
        request (Request): The request object.
        candidature (Candidature): The candidature.

    Returns:
        dict: Error message if validation fails, None otherwise.
    """
    check_mx = not (ADMIN_EMAIL.split("@")[-1] in email.split("@")[-1])
    email_error = is_valid_email(email, request, check_mx)
    if email_error is not None:
        return {
            'candidature': candidature, 
            'MemberTypes': MemberTypes, 
            'error': email_error['error']
        }
    if choice not in MemberTypes.get_names() \
        or choice not in [MemberTypes.ORDINARY.name, MemberTypes.COOPERATOR.name]:
        return {
            'candidature': candidature, 
            'MemberTypes': MemberTypes,
            'error': _('invalid_choice')
        }

    candidature.email = email
    candidature.type = getattr(MemberTypes, choice, None)

    return None

def attempt_send_validation_email(request: Request, 
                                  candidature: Candidature) -> bool:
    """
    Try sending a validation email to the candidate.

    Args:
        request (Request): The request object.
        candidature (Candidature): The candidature.

    Returns:
        bool: True if email sent, False otherwise.
    """
    candidature.add_email_send_status(
        EmailSendStatus.IN_PREPARATION, 
        "send_validation_email"
    )
    if send_validation_email(request, candidature):
        candidature.add_email_send_status(
            EmailSendStatus.SENT, 
            "send_validation_email"
        )
        return True
    else:
        candidature.add_email_send_status(
            EmailSendStatus.ERROR, 
            "send_validation_email"
        )
        return False

def commit_candidature_changes(request: Request, 
                               candidature: Candidature) -> dict:
    """
    Commit changes to the candidature in the database.

    Args:
        request (Request): The request object.
        candidature (Candidature): The candidature.

    Returns:
        dict: The updated candidature data.
    """
    candidatures = get_candidatures(request)
    candidatures[candidature.oid] = candidature
    candidatures.monitored_members[candidature.oid] = candidature

    try:
        request.tm.commit()
        candidature.add_email_send_status(
            EmailSendStatus.SENT,
            "send_validation_email"
        )
        return {'candidature': candidature, 'MemberTypes': MemberTypes}
    except Exception as e:
        log.error(
            f"Error committing candidature {candidature.oid}: {e}"
        )
        # Explicitly abort the transaction to ensure consistency
        request.tm.abort()
        # Return error message
        return {
            'candidature': candidature,
            'MemberTypes': MemberTypes,
            'error': _('error_committing_candidature')
        }

def handle_email_validation_state(
        request: Request,
        candidature: Candidature
    ) -> dict:
    """
    Process the email validation state of a candidature.

    Validates the response to the email challenge and updates the candidature
    state upon successful validation.

    Args:
        request (Request): The Pyramid request object.
        candidature (Candidature): The candidature object.

    Returns:
        dict: Response dictionary containing candidature data, form rendering,
              and error messages as needed.
    """
    log.debug(f"Handling email validation state for candidature id:{id(candidature)}, oid:{candidature.oid}")
    if 'submit' in request.POST:
        # Validate the challenge
        challenge_error = validate_challenge(request, candidature)
        if challenge_error:
            return challenge_error
        
        # User is a human, we update state and commit changes
        candidature.candidature_state = CandidatureStates.CONFIRMED_HUMAN
        try:
            request.tm.commit()
            # Send confirmation email and handle status
            send_result = send_confirm_validation_email(request, candidature)
            if send_result.get('error'):        
                candidature.add_email_send_status(
                    EmailSendStatus.ERROR, 
                    'send_confirm_validation_email'
                )
            else:
                return {
                    'form': render_candidature_form(request, candidature),
                    'candidature': candidature,
                    'MemberTypes': MemberTypes
                }
        except Exception as e:
            log.error(f"Error committing candidature {candidature.oid}: {e}")
            # Explicitly abort the transaction to ensure consistency
            request.tm.abort()
            candidature.add_email_send_status(
                EmailSendStatus.ERROR, 
                'send_confirm_validation_email'
            )

            return {
                'candidature': candidature,
                'MemberTypes': MemberTypes,
                'error': _('error_committing_candidature')
            }
    return {
        'candidature': candidature,
        'MemberTypes': MemberTypes
    }

def validate_challenge(
        request: Request, 
        candidature: Candidature
    ) -> Optional[dict]:
    """
    Validate the math challenge response from the candidate.

    Args:
        request (Request): The request object.
        candidature (Candidature): The candidature object.

    Returns:
        dict: Error message if validation fails, None otherwise.
    """
    for key, attended_result in candidature.challenge.items():
        label = f"result_{key}"
        if request.params[label].strip() != str(attended_result[1]):
            return {
                'error': _('invalid_challenge'), 
                'candidature': candidature, 
                'MemberTypes': MemberTypes
            }
    return None

def render_candidature_form(request: Request, 
                            candidature: Candidature) -> str:
    """
    Render the candidature form based on the candidature type.

    Args:
        request (Request): The request object.
        candidature (Candidature): The candidature object.

    Returns:
        str: The HTML rendering of the candidature form.
    """
    schema = RegisterForm().bind(request=request)
    appstruct = {
        'cooperative_number': candidature.oid,
        'email': candidature.email,
    }
    if candidature.type == MemberTypes.ORDINARY:
        schema.prepare_for_ordinary()
    form = deform.Form(schema, buttons=('submit',), translator=Translator)
    return form.render(appstruct=appstruct)

def handle_confirmed_human_state(request, candidature):
    """Handle the confirmed human state.

    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature

    Returns:
        HTTPFound: the HTTP found response
    """
    log.debug(f"Handling confirmed human state for candidature id:{id(candidature)}, oid:{candidature.oid}")
    schema = RegisterForm().bind(request=request)
    permissions = get_access_permissions(candidature, candidature)
    if not permissions or permissions == Permissions.NONE:
        log.warning(
            f'No permission to access member datas: {candidature.oid}'
        )
        request.session.flash(_('no_permission'), 'error')
        return {
            "error":_('no_permission'),
            "member": None,
            "form": None,
            "candidature": candidature,
            'MemberTypes': candidature.type
        }
    schema.apply_permissions(permissions.data, {'password_confirm':Permissions.ACCESS|Permissions.READ|Permissions.WRITE, 'password':Permissions.ACCESS|Permissions.READ|Permissions.WRITE})
    schema.apply_permissions(permissions)
    appstruct = {
        'cooperative_number': candidature.oid,
        'email': candidature.email,
    }
    if candidature.type == MemberTypes.ORDINARY:
        schema.prepare_for_ordinary()

    form = deform.Form(schema, buttons=('submit',), translator=Translator)
    if 'submit' in request.POST:
        try:
            items = request.POST.items()
            appstruct.update(dict(items))
            #form.validate(items) #@TODO resolve the error 
        except ValidationFailure as e:
            return {
                'form': form.render(appstruct=appstruct),
                'candidature': candidature,
                'MemberTypes': MemberTypes
            }
        candidatures = get_candidatures(request)
        password = request.params['password'] if 'password' in request.params else None
        password_confirm = request.params['password_confirm'] if 'password_confirm' in request.params else None
        pseudonym = request.params['pseudonym'] if 'pseudonym' in request.params else None
        if not password or not password_confirm or not pseudonym:
            return {
                'form': form.render(appstruct=appstruct),
                'error': _('missing_data'),
                'candidature': candidature,
                'MemberTypes': MemberTypes
            }
        appstruct['pseudonym'] = pseudonym
        is_valid_password_result = is_valid_password(password)
        if is_valid_password_result:
            is_valid_password_result.update(
                {
                    'form': form.render(appstruct=appstruct),
                    'candidature': candidature,
                    'MemberTypes': MemberTypes
                }
            )
            return is_valid_password_result
        
        if password != password_confirm:
            return {
                'form': form.render(appstruct=appstruct),
                'error': _('passwords_dont_match'),
                'candidature': candidature,
                'MemberTypes': MemberTypes
            }

        is_valid_pseudo_result = is_valid_unique_pseudonym(pseudonym)
        if is_valid_pseudo_result:
            is_valid_pseudo_result.update(
                {
                    'form': form.render(appstruct=appstruct),
                    'candidature': candidature,
                    'MemberTypes': MemberTypes
                }
            )
            return is_valid_pseudo_result
        candidature.pseudonym = pseudonym
        if 'fullname' in request.params:
            appstruct['fullname'] = request.params['fullname']
        if 'fullsurname' in request.params:
            appstruct['fullsurname'] = request.params['fullsurname']
        if 'nationality' in request.params:
            appstruct['nationality'] = request.params['nationality']
        if 'lang1' in request.params:
            appstruct['lang1'] = request.params['lang1']
        if 'lang2' in request.params:
            appstruct['lang2'] = request.params['lang2']
        if 'lang3' in request.params:
            appstruct['lang3'] = request.params['lang3']
        if 'description' in request.params:
            appstruct['description'] = request.params['description']
        parameters = {}
        for field_name in MemberDatas.__dataclass_fields__.keys():
            if field_name not in request.params:
                continue
            value = request.params[field_name]
            if field_name in ('lang2', 'lang3') and not value:
                continue
            parameters[field_name] = value
        # @TODO use permission than member type to manipulate the data
        if candidature.type == MemberTypes.COOPERATOR:
            # Extract birthdate from request only for coopereator
            # This is a bit convoluted because of the way deform handles nested forms
            start_birthdate = False
            birthdate = None
            for k,v in request.params.items():
                if k == '__start__' and v == 'birthdate:mapping':
                    start_birthdate = True
                elif start_birthdate and k == 'date':
                    birthdate = v
                    break
                elif start_birthdate and k == '__end__' and v == 'birthdate:mapping':
                    break
            if birthdate:
                try:
                    parameters['birthdate'] = datetime.datetime.strptime(
                    birthdate[:LDAP_TIME_LENGTH] if len(birthdate) >= LDAP_TIME_LENGTH else (birthdate[:LDAP_DATE_LENGTH]+LDAP_DEFAULT_HOUR),
                    LDAP_TIME_FORMAT
                    )
                except ValueError:
                    return {
                        'form': form.render(appstruct=appstruct),
                        'error': _('invalid_date'),
                        'candidature': candidature,
                        'MemberTypes': MemberTypes
                    }
            else:
                log.error("Birthdate not found in request")
                return {
                    'form': form.render(appstruct=appstruct),
                    'error': _('missing_data'),
                    'candidature': candidature,
                    'MemberTypes': MemberTypes
                }
        data = MemberDatas(**parameters)
        candidature.data = data

        candidature.pseudonym = request.params['pseudonym']
        match candidature.type:
            case MemberTypes.ORDINARY:
                result = register_user_to_ldap(request, candidature, password)
                if result['status'] == 'error':
                    return {
                        'form': form.render(appstruct=appstruct),
                        'error': result['message'],
                        'candidature': candidature,
                        'MemberTypes': MemberTypes
                    }
                candidatures.monitored_members.pop(candidature.oid, None)
                candidature.candidature_state = CandidatureStates.APPROVED
                email_template = "send_candidature_approuved_email"
            case MemberTypes.COOPERATOR:
                candidature.candidature_state = CandidatureStates.UNIQUE_DATA
                email_template = "send_candidature_pending_email"

            case _: # should never happen
                return {
                    'form': form.render(appstruct=appstruct),
                    'error': _('invalid_choice'),
                    'candidature': candidature,
                    'MemberTypes': MemberTypes
                }

        send_candidature_state_change_email(
            request,
            candidature,
            email_template
        )
        transaction = request.tm
        try:
            transaction.commit()
            candidature.add_email_send_status(
                EmailSendStatus.SENT,
                email_template
            )
        except Exception as e:
            log.error(
                f"Error while commiting candidature {candidature.oid} : {e}"
            )
            candidature.add_email_send_status(
                EmailSendStatus.ERROR,
                email_template
            )
        if candidature.type == MemberTypes.COOPERATOR:
            if err := prepare_for_cooperator(request, candidature):
                return err
            return get_template_parameters_for_cooperator(request, candidature)
    
    return {
        'form': form.render(appstruct=appstruct),
        'candidature': candidature,
        'MemberTypes': MemberTypes
    }

def prepare_for_cooperator(
        request:Request,
        candidature:Candidature
    ) -> Optional[dict]:
    """Prepare the candidature for a cooperator.

    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature

    Returns:
        Optional[dict]: the error dictionary or None
    """
    if not candidature.voters:
        transaction = request.tm
        try:
            voters = random_voters(request)
            candidature.voters = [
                Voter(voter["uid"], voter["mail"], voter["cn"])
                for voter in voters
            ]
            transaction.commit()
        except Exception as e:
            log.error(
                f"Error while commiting candidature {candidature.oid} : {e}"
            )
            return {
                'candidature': candidature,
                'MemberTypes': MemberTypes,
                'error': _('voters_not_selected'),
                'voting_url': request.route_url(
                    'vote',
                    _query={'oid': candidature.oid}
                ),
                'signature': MAIL_SIGNATURE.format(
                    site_name=request.registry.settings.get('site_name'),
                    domain_name=request.registry.settings.get('domain_name'),
                    organization_details=request.registry.settings.get('organization_details'),
                    fullname = candidature.data.fullname,
                    fullsurname = candidature.data.fullsurname,
                )
            }
    return None

def _notify_verifiers_of_submission(
        request: Request,
        candidature: Candidature
    ) -> None:
    """Inform selected verifiers that a candidature is awaiting their review."""
    if not candidature.voters or getattr(candidature, 'verifiers_notified', False):
        return
    domain_name = request.registry.settings.get('domain_name')
    organization_details = request.registry.settings.get('organization_details')
    voting_url = request.route_url('vote', _query={'oid': candidature.oid})
    if isinstance(voting_url, tuple):
        voting_url = voting_url[0]

    deadline = getattr(candidature, 'verification_deadline', None)
    if not deadline:
        deadline = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            days=VERIFIER_VOTE_DEADLINE_DAYS
        )
        candidature.verification_deadline = deadline
    date_end_vote = deadline.strftime('%Y-%m-%d')

    candidate_data = getattr(candidature, 'data', None)
    format_vars = {
        'subject_url': voting_url,
        'date_end_vote': date_end_vote,
        'subject_email': candidature.email or '',
        'subject_last_name': getattr(candidate_data, 'fullsurname', '') if candidate_data else '',
        'subject_first_name': getattr(candidate_data, 'fullname', '') if candidate_data else '',
        'birth_date': _format_birthdate(getattr(candidate_data, 'birthdate', None)) if candidate_data else '',
        'citizenship': getattr(candidate_data, 'nationality', '') if candidate_data else '',
    }

    for voter in candidature.voters:
        if not voter.email:
            continue
        template_path = _resolve_inform_verifier_template(
            _get_voter_language(request, voter)
        )
        template_vars = {
            'domain_name': domain_name,
            'organization_details': organization_details,
            'verifier': _get_verifier_name(request, voter),
        }
        try:
            success = send_email(
                request,
                subject=None,
                recipients=[voter.email],
                template_path=template_path,
                template_vars=template_vars,
                format_vars=format_vars,
                derive_subject_from_title=True
            )
            if not success:
                log.error(
                    "Unable to queue verification email for %s regarding candidature %s",
                    voter.email,
                    candidature.oid
                )
        except Exception as exc:
            log.error(
                "Error while notifying verifier %s for candidature %s: %s",
                voter.email,
                candidature.oid,
                exc
            )
    candidature.verifiers_notified = True

def _resolve_inform_verifier_template(language: Optional[str]) -> str:
    lang = (language or 'en').lower()
    lang = lang.split('_')[0].split('-')[0]
    template = INFORM_VERIFIER_TEMPLATE.format(lang=lang)
    try:
        return VERIFIER_TEMPLATE_RESOLVER.resolve(template).abspath()
    except Exception as exc:
        log.error(
            "Error resolving verifier template for %s (%s), fallback to English.",
            lang,
            exc
        )
        fallback = INFORM_VERIFIER_TEMPLATE.format(lang='en')
        return VERIFIER_TEMPLATE_RESOLVER.resolve(fallback).abspath()

def _get_voter_language(request: Request, voter: Voter) -> Optional[str]:
    member = get_member_by_oid(voter.oid, request, True)
    if member and getattr(member, 'data', None):
        return getattr(member.data, 'lang1', None)
    return None

def _get_verifier_name(request: Request, voter: Voter) -> str:
    member = get_member_by_oid(voter.oid, request, True)
    if member and getattr(member, 'data', None):
        first_name = getattr(member.data, 'fullname', '')
        last_name = getattr(member.data, 'fullsurname', '')
        full_name = " ".join(part for part in [first_name, last_name] if part)
        if full_name.strip():
            return full_name
    return voter.pseudonym

def _format_birthdate(birthdate: Optional[datetime.date]) -> str:
    if isinstance(birthdate, datetime.datetime):
        return birthdate.strftime('%Y-%m-%d')
    if isinstance(birthdate, datetime.date):
        return birthdate.strftime('%Y-%m-%d')
    return str(birthdate) if birthdate else ''

def get_template_parameters_for_cooperator(
        request:Request,
        candidature:Candidature
    )->dict:
    """Get the template parameters for a cooperator.
    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature
    Returns:
        dict: the template parameters
    """
    voting_url = request.route_url('vote', _query={'oid': candidature.oid}),
    if(isinstance(voting_url, tuple)):
        voting_url = voting_url[0]
    site_name=request.registry.settings.get('site_name')
    domain_name = request.registry.settings.get('domain_name')
    organization_details = request.registry.settings.get('organization_details')
    signature = MAIL_SIGNATURE.format(
        site_name=site_name,
        domain_name=domain_name,
        organization_details=organization_details,
        fullname = candidature.data.fullname,
        fullsurname = candidature.data.fullsurname if getattr(
            candidature.data,
            'fullsurname',
            f"{site_name} team"
        ) else "",
    )
    local_datas = {
        "voting_url":voting_url,
        "signature":signature,
        "site_name":site_name,
        "organization_details":organization_details,
        "domain_name":domain_name,
    }
    email_copy_id_verification_body = _(
        "email_copy_id_verification_body",
        local_datas
    )
    email_video_id_verification_body = _(
        "email_video_id_verification_body",
        local_datas
    )

    return {
        'candidature': candidature,
        'MemberTypes': MemberTypes,
        'voters': candidature.voters,
        'data_email_video_id_verification_subject':_("email_video_id_verification_subject", local_datas),
        'data_email_video_id_verification_body': email_video_id_verification_body,
        'data_email_copy_id_verification_subject':_("email_copy_id_verification_subject", local_datas),
        'data_email_copy_id_verification_body':email_copy_id_verification_body,
    }

def handle_unique_data_state(request, candidature):
    """Handle the unique data state.

    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature

    Returns:
        HTTPFound: the HTTP found response
    """
    log.debug(f"Handling unique data state for candidature id:{id(candidature)}, oid:{candidature.oid}")
    if not candidature.voters:
        prepare_for_cooperator(request, candidature)
    if 'confirm' in request.POST:
        #Get identity Verification method

        candidatures = get_candidatures(request)
        candidature.candidature_state = CandidatureStates.PENDING
        transaction = request.tm
        try:
            transaction.commit()
            candidature.add_email_send_status(
                EmailSendStatus.SENT,
                "send_candidature_pending_email"
            )
            _notify_verifiers_of_submission(request, candidature)
            transaction.commit()
            return {
                'candidature': candidature,
                'MemberTypes': MemberTypes,
            }

        except Exception as e:
            log.error(
                f"Error while commiting candidature {candidature.oid} : {e}"
            )
            candidature.add_email_send_status(
                EmailSendStatus.ERROR,
                "send_candidature_pending_email"
            )

    return get_template_parameters_for_cooperator(request, candidature)


def handle_pending_state(request, candidature):
    """Handle the pending state.

    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature

    Returns:
        HTTPFound: the HTTP found response
    """
    log.debug(f"Handling pending state for candidature id:{id(candidature)}, oid:{candidature.oid}")
    return {
        'candidature': candidature,
        'MemberTypes': MemberTypes,
    }

def handle_default_state(request, candidature):
    """Handle the default state.

    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature

    Returns:
        HTTPFound: the HTTP found response
    """
    log.error(f"Unhandled candidature state: {candidature.candidature_state}")
    return {
        'candidature': candidature,
        'MemberTypes': MemberTypes,
        'error':"handle_default_state Not yet implemented"
    }
