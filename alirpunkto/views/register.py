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
    CANDIDATURE_OID,
    MEMBER_OID,
    SEED_LENGTH,
    log,
    SITE_NAME,
    DOMAIN_NAME,
)
from pyramid.i18n import Translator
from ..utils import (
    get_candidatures,
    generate_math_challenges, is_valid_email,
    register_user_to_ldap,
    is_valid_password, is_valid_unique_pseudonym, random_voters,
    send_validation_email,
    send_confirm_validation_email,
    send_candidature_state_change_email,
    retrieve_candidature,
)
import json

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
    log.debug(f"Handling draft state for candidature {candidature.oid}")
    if 'submit' in request.POST:
        email = request.params['email']
        choice = request.params['choice']

        error = validate_candidature_choice_and_email(
            email, choice, request, candidature
        )
        if error:
            return error

        candidature.challenge = generate_math_challenges(request)

        if not attempt_send_validation_email(request, candidature):
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
    email_error = is_valid_email(email, request)
    if email_error is not None:
        return {
            'candidature': candidature, 
            'MemberTypes': MemberTypes, 
            'error': email_error['error']
        }

    if choice not in MemberTypes.get_names():
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
    log.debug(f"Handling email validation state for candidature {candidature.oid}")
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
            candidature.add_email_send_status(
                EmailSendStatus.ERROR, 
                'send_confirm_validation_email'
            )
            # Explicitly abort the transaction to ensure consistency
            request.tm.abort()
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
    log.debug(f"Handling confirmed human state for candidature {candidature.oid}")
    schema = RegisterForm().bind(request=request)
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
        parameters = {
            k: request.params[k]
            for k in MemberDatas.__dataclass_fields__.keys()
            if k in request.params
        }
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
                    birthdate, '%Y-%m-%d'
                    ).date()
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
                    fullname = candidature.data.fullname,
                    fullsurname = candidature.data.fullsurname,
                )
            }
    return None

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
    signature = MAIL_SIGNATURE.format(
        site_name=site_name,
        domain_name=request.registry.settings.get('domain_name'),
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
        "site_name":request.registry.settings.get('site_name'),
        "domain_name":request.registry.settings.get('domain_name')
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
    log.debug(f"Handling unique data state for candidature {candidature.oid}")
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
    log.debug(f"Handling pending state for candidature {candidature.oid}")
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

