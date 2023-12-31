# description: Register view
#   A candidate submits their application through the "register" view on the site.
#   The site verifies that the candidate is not already registered.
#   The site collects their information and sends them an email to confirm their application submission.
#   The site creates an application object and randomly selects 3 members from the LDAP members if possible, otherwise the administrator.
#   The site invites voters to vote for or against the application.
# author: Michaël Launay
# date: 2023-06-15

from dataclasses import dataclass
import datetime
from typing import Dict, List, Optional, Tuple
import deform
from deform import ValidationFailure
from pyramid.view import view_config
from pyramid.request import Request
from pyramid.httpexceptions import HTTPFound
from ..schemas.register_form import RegisterForm
from ..models.candidature import (
    Candidature, CandidatureStates, 
    CandidatureTypes,
    CandidatureEmailSendStatus, CandidatureData,
    Voter,
    CANDIDATURE_OID,
    SEED_LENGTH
)
from .. import _, MAIL_SIGNATURE
from pyramid.i18n import Translator, get_localizer
import logging
log = logging.getLogger("alirpunkto")
from ..utils import (
    get_candidatures, decrypt_oid,
    generate_math_challenges, is_valid_email, get_candidature_by_oid,
    register_user_to_ldap,
    is_valid_password, is_valid_unique_pseudonym, random_voters,
    send_validation_email,
    send_confirm_validation_email,
    send_candidature_state_change_email,
)



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
    candidature, error = _retrieve_candidature(request)

    if error:
        return error

    # Handle the current state of the candidature process
    return _handle_candidature_state(request, candidature)

def _retrieve_candidature(
        request: Request
    ) -> (Candidature, Dict):
    """Retrieve an existing candidature from the session or URL.

    Parameters:
    - request (Request): The pyramid request object.

    Returns:
    - tuple: A tuple containing the candidature object and an error dict if applicable.
    """
    # Check if the candidature is already in the request
    candidatures = get_candidatures(request)
    if CANDIDATURE_OID in request.session and \
       request.session[CANDIDATURE_OID] in candidatures:
        return candidatures[request.session[CANDIDATURE_OID]], None

    # If the candidature is not in the request, try to retrieve it from the URL
    encrypted_oid = request.params.get("oid", None)
    if encrypted_oid:
        decrypted_oid, seed = decrypt_oid(
            encrypted_oid,
            SEED_LENGTH,
            request.registry.settings['session.secret'])
        candidature = get_candidature_by_oid(decrypted_oid, request)
        if candidature is None:
            error = _('candidature_not_found')
            return None, {'candidature': candidature,
                'CandidatureTypes': CandidatureTypes,
                'error': error}
        if seed != candidature.email_send_status_history[-1].seed:
            error = _('url_is_obsolete')
            return None, {'candidature': candidature,
                'CandidatureTypes': CandidatureTypes,
                'error': error,
                'url_obsolete': True}
        request.session[CANDIDATURE_OID] = candidature.oid
        return candidature, None
    else:
        # Create a new candidature and store its OID in the session
        candidature = Candidature()
        request.session[CANDIDATURE_OID] = candidature.oid
        return candidature, None

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
    match candidature.state:
        case CandidatureStates.DRAFT:
            return handle_draft_state(request, candidature)
        case CandidatureStates.EMAIL_VALIDATION:
            return handle_email_validation_state(request, candidature)
        case CandidatureStates.CONFIRMED_HUMAN:
            return handle_confirmed_human_state(request, candidature)
        case CandidatureStates.UNIQUE_DATA:
            return handle_unique_data_state(request, candidature)
        case CandidatureStates.PENDING:
            return handle_pending_state(request, candidature)
        case CandidatureStates.APPROVED:
            return handle_pending_state(request, candidature)
        case CandidatureStates.REFUSED:
            return handle_pending_state(request, candidature)
        case _:
            log.error("Candidature state not handled: %s", candidature.state)
            return handle_default_state(request, candidature)

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
                'CandidatureTypes': CandidatureTypes,
                'error': _('email_not_sent')
            }

        candidature.state = CandidatureStates.EMAIL_VALIDATION
        return commit_candidature_changes(request, candidature)

    return {'candidature': candidature, 'CandidatureTypes': CandidatureTypes}

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
            'CandidatureTypes': CandidatureTypes, 
            'error': email_error['error']
        }

    if choice not in CandidatureTypes.get_names():
        return {
            'candidature': candidature, 
            'CandidatureTypes': CandidatureTypes,
            'error': _('invalid_choice')
        }

    candidature.email = email
    candidature.type = getattr(CandidatureTypes, choice, None)

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
        CandidatureEmailSendStatus.IN_PREPARATION, 
        "send_validation_email"
    )
    if send_validation_email(request, candidature):
        candidature.add_email_send_status(
            CandidatureEmailSendStatus.SENT, 
            "send_validation_email"
        )
        return True
    else:
        candidature.add_email_send_status(
            CandidatureEmailSendStatus.ERROR, 
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
    candidatures.monitored_candidatures[candidature.oid] = candidature

    try:
        request.tm.commit()
        candidature.add_email_send_status(
            CandidatureEmailSendStatus.SENT,
            "send_validation_email"
        )
        return {'candidature': candidature, 'CandidatureTypes': CandidatureTypes}
    except Exception as e:
        log.error(
            f"Error committing candidature {candidature.oid}: {e}"
        )
        return {
            'candidature': candidature,
            'CandidatureTypes': CandidatureTypes,
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
    if 'submit' in request.POST:
        # Validate the challenge
        challenge_error = validate_challenge(request, candidature)
        if challenge_error:
            return challenge_error
        
        # User is a human, we update state and commit changes
        candidature.state = CandidatureStates.CONFIRMED_HUMAN
        try:
            request.tm.commit()
            # Send confirmation email and handle status
            send_result = send_confirm_validation_email(request, candidature)
            if send_result.get('error'):        
                candidature.add_email_send_status(
                    CandidatureEmailSendStatus.ERROR, 
                    'send_confirm_validation_email'
                )
            else:
                return {
                    'form': render_candidature_form(request, candidature),
                    'candidature': candidature,
                    'CandidatureTypes': CandidatureTypes
                }
        except Exception as e:
            log.error(f"Error committing candidature {candidature.oid}: {e}")
            candidature.add_email_send_status(
                CandidatureEmailSendStatus.ERROR, 
                'send_confirm_validation_email'
            )
            return {
                'candidature': candidature,
                'CandidatureTypes': CandidatureTypes,
                'error': _('error_committing_candidature')
            }
    return {
        'candidature': candidature,
        'CandidatureTypes': CandidatureTypes
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
                'CandidatureTypes': CandidatureTypes
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
    if candidature.type == CandidatureTypes.ORDINARY:
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
    schema = RegisterForm().bind(request=request)
    appstruct = {
        'cooperative_number': candidature.oid,
        'email': candidature.email,
    }
    if candidature.type == CandidatureTypes.ORDINARY:
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
                'CandidatureTypes': CandidatureTypes
            }
        candidatures = get_candidatures(request)
        password = request.params['password']
        password_confirm = request.params['password_confirm']
        pseudonym = request.params['pseudonym']
        appstruct['pseudonym'] = pseudonym
        is_valid_password_result = is_valid_password(password)
        if is_valid_password_result:
            is_valid_password_result.update(
                {
                    'form': form.render(appstruct=appstruct),
                    'candidature': candidature,
                    'CandidatureTypes': CandidatureTypes
                }
            )
            return is_valid_password_result
        
        if password != password_confirm:
            return {
                'form': form.render(appstruct=appstruct),
                'error': _('passwords_dont_match'),
                'candidature': candidature,
                'CandidatureTypes': CandidatureTypes
            }

        is_valid_pseudo_result = is_valid_unique_pseudonym(pseudonym)
        if is_valid_pseudo_result:
            is_valid_pseudo_result.update(
                {
                    'form': form.render(appstruct=appstruct),
                    'candidature': candidature,
                    'CandidatureTypes': CandidatureTypes
                }
            )
            return is_valid_pseudo_result
        
        candidature.pseudonym = pseudonym

        if candidature.type == CandidatureTypes.ORDINARY:
            result = register_user_to_ldap(request, candidature, password)
            if result['status'] == 'error':
                return {
                    'form': form.render(appstruct=appstruct),
                    'error': result['message'],
                    'candidature': candidature,
                    'CandidatureTypes': CandidatureTypes
                }
            candidatures.monitored_candidatures.pop(candidature.oid, None)
            candidature.state = CandidatureStates.APPROVED
            email_template = "send_candidature_approuved_email"

        elif candidature.type == CandidatureTypes.COOPERATOR:
            appstruct['fullname'] = request.params['fullname']
            appstruct['fullsurname'] = request.params['fullsurname']
            appstruct['nationality'] = request.params['nationality']
            appstruct['lang1'] = request.params['lang1']
            appstruct['lang2'] = request.params['lang2']
            parameters = {
                k: request.params[k]
                for k in CandidatureData.__dataclass_fields__.keys()
                if k in request.params
            }
            try:
                parameters['birthdate'] = datetime.datetime.strptime(
                    request.params['date'], '%Y-%m-%d'
                ).date()
            except ValueError:
                return {
                    'form': form.render(appstruct=appstruct),
                    'error': _('invalid_date'),
                    'candidature': candidature,
                    'CandidatureTypes': CandidatureTypes
                }
            data = CandidatureData(**parameters)
            candidature.data = data

            candidature.pseudonym = request.params['pseudonym']
            candidature.state = CandidatureStates.UNIQUE_DATA
            email_template = "send_candidature_pending_email"

        else:
            return {
                'form': form.render(appstruct=appstruct),
                'error': _('invalid_choice'),
                'candidature': candidature,
                'CandidatureTypes': CandidatureTypes
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
                CandidatureEmailSendStatus.SENT,
                email_template
            )
        except Exception as e:
            log.error(
                f"Error while commiting candidature {candidature.oid} : {e}"
            )
            candidature.add_email_send_status(
                CandidatureEmailSendStatus.ERROR,
                email_template
            )
        if candidature.type == CandidatureTypes.COOPERATOR:
            if err := prepare_for_cooperator(request, candidature):
                return err
            return get_template_parameters_for_cooperator(request, candidature)
    
    return {
        'form': form.render(appstruct=appstruct),
        'candidature': candidature,
        'CandidatureTypes': CandidatureTypes
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
                Voter(voter["mail"], voter["sn"])
                for voter in voters
            ]
            transaction.commit()
        except Exception as e:
            log.error(
                f"Error while commiting candidature {candidature.oid} : {e}"
            )
            return {
                'candidature': candidature,
                'CandidatureTypes': CandidatureTypes,
                'error': _('voters_not_selected'),
                'voting_url': request.route_url(
                    'vote',
                    _query={'oid': candidature.oid}
                ),
                'signature': MAIL_SIGNATURE.format(
                    site_name=request.registry.settings.get('site_name'),
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
    return {
        'candidature': candidature,
        'CandidatureTypes': CandidatureTypes,
        'voters': candidature.voters,
        'voting_url': request.route_url('vote', _query={'oid': candidature.oid}),
        'signature': MAIL_SIGNATURE.format(
            site_name=request.registry.settings.get('site_name'),
            fullname = candidature.data.fullname,
            fullsurname = candidature.data.fullsurname if getattr(
                candidature.data,
                'fullsurname',
                "Alirpunkto team"
            ) else "",
        )
    }


def handle_unique_data_state(request, candidature):
    """Handle the unique data state.

    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature

    Returns:
        HTTPFound: the HTTP found response
    """
    if not candidature.voters:
        prepare_for_cooperator(request, candidature)
    if 'confirm' in request.POST:
        #Get identity Verification method

        candidatures = get_candidatures(request)
        candidature.state = CandidatureStates.PENDING
        transaction = request.tm
        try:
            transaction.commit()
            candidature.add_email_send_status(
                CandidatureEmailSendStatus.SENT,
                "send_candidature_pending_email"
            )
            transaction.commit()
            return {
                'candidature': candidature,
                'CandidatureTypes': CandidatureTypes,
            }

        except Exception as e:
            log.error(
                f"Error while commiting candidature {candidature.oid} : {e}"
            )
            candidature.add_email_send_status(
                CandidatureEmailSendStatus.ERROR,
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
    return {
        'candidature': candidature,
        'CandidatureTypes': CandidatureTypes,
    }

def handle_default_state(request, candidature):
    """Handle the default state.

    Args:
        request (pyramid.request.Request): the request
        candidature (Candidature): the candidature

    Returns:
        HTTPFound: the HTTP found response
    """
    return {
        'candidature': candidature,
        'CandidatureTypes': CandidatureTypes,
        'error':"handle_default_state Not yet implemented"
    }

